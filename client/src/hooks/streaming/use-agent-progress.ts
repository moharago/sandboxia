/**
 * Agent Progress SSE Hook
 *
 * 에이전트 실행 진행 상태를 SSE로 수신하는 훅
 *
 * @example
 * ```tsx
 * const { status, progress, completedNodes, start } = useAgentProgress({
 *   agentType: "eligibility_evaluator",
 *   projectId: "uuid-...",
 *   onNodeComplete: (nodeId) => console.log(`${nodeId} 완료`),
 *   onComplete: () => console.log("분석 완료"),
 * })
 *
 * // 분석 시작
 * <button onClick={start}>분석 시작</button>
 *
 * // 진행 상태 표시
 * <ProgressBar value={progress} />
 * ```
 */

import { useAuthStore } from "@/stores/auth-store"
import type {
    AgentProgressEvent,
    AgentType,
    SSEConnectionStatus,
    UseAgentProgressReturn,
} from "@/types/api/agent-progress"
import { useCallback, useRef, useState } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""

/** 에이전트별 스트리밍 엔드포인트 */
const STREAM_ENDPOINTS: Record<AgentType, string> = {
    service_structurer: "/api/v1/agents/progress/stream/service",
    eligibility_evaluator: "/api/v1/agents/progress/stream/eligibility",
    track_recommender: "/api/v1/agents/progress/stream/track",
    application_drafter: "/api/v1/agents/progress/stream/draft",
}

interface UseAgentProgressOptions {
    /** 에이전트 타입 */
    agentType: AgentType
    /** 프로젝트 ID */
    projectId: string
    /** 노드 완료 시 콜백 */
    onNodeComplete?: (nodeId: string) => void
    /** 에이전트 완료 시 콜백 */
    onComplete?: () => void
    /** 에러 발생 시 콜백 */
    onError?: (error: string) => void
}

/**
 * 에이전트 진행 상태 SSE 훅
 */
export function useAgentProgress(
    options: UseAgentProgressOptions
): UseAgentProgressReturn {
    const { agentType, projectId, onNodeComplete, onComplete, onError } = options

    const [status, setStatus] = useState<SSEConnectionStatus>("idle")
    const [progress, setProgress] = useState(0)
    const [currentNodeId, setCurrentNodeId] = useState<string | null>(null)
    const [completedNodes, setCompletedNodes] = useState<string[]>([])
    const [message, setMessage] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const abortControllerRef = useRef<AbortController | null>(null)

    const start = useCallback(async () => {
        // 이미 실행 중이면 무시
        if (status === "connecting" || status === "connected") {
            return
        }

        // 상태 초기화
        setStatus("connecting")
        setProgress(0)
        setCurrentNodeId(null)
        setCompletedNodes([])
        setMessage(null)
        setError(null)

        // 인증 토큰 가져오기
        const token = await useAuthStore.getState().getAccessToken()
        if (!token) {
            setStatus("error")
            setError("로그인이 필요합니다.")
            onError?.("로그인이 필요합니다.")
            return
        }

        // AbortController 생성
        abortControllerRef.current = new AbortController()

        try {
            const endpoint = STREAM_ENDPOINTS[agentType]
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ project_id: projectId }),
                signal: abortControllerRef.current.signal,
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
                throw new Error(errorData.detail || `Request failed: ${response.status}`)
            }

            setStatus("connected")

            // ReadableStream으로 SSE 파싱
            const reader = response.body?.getReader()
            if (!reader) {
                throw new Error("Response body is not readable")
            }

            const decoder = new TextDecoder()
            let buffer = ""

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })

                // SSE 이벤트 파싱 (data: {...}\n\n)
                const lines = buffer.split("\n\n")
                buffer = lines.pop() || "" // 마지막 불완전한 청크는 버퍼에 유지

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const jsonStr = line.slice(6) // "data: " 제거
                            const event: AgentProgressEvent = JSON.parse(jsonStr)

                            // 이벤트 타입별 처리
                            switch (event.event_type) {
                                case "agent_start":
                                    setMessage(event.message || "분석을 시작합니다...")
                                    break

                                case "node_start":
                                    setCurrentNodeId(event.node_id || null)
                                    setProgress(event.progress)
                                    setMessage(event.message || null)
                                    break

                                case "node_end":
                                    setCompletedNodes(event.completed_nodes)
                                    setProgress(event.progress)
                                    setMessage(event.message || null)
                                    if (event.node_id) {
                                        onNodeComplete?.(event.node_id)
                                    }
                                    break

                                case "agent_end":
                                    setStatus("completed")
                                    setProgress(100)
                                    setCurrentNodeId(null)
                                    setMessage(event.message || "분석이 완료되었습니다.")
                                    onComplete?.()
                                    break

                                case "error":
                                    setStatus("error")
                                    setError(event.message || "오류가 발생했습니다.")
                                    onError?.(event.message || "오류가 발생했습니다.")
                                    break
                            }
                        } catch (parseError) {
                            console.error("SSE 파싱 오류:", parseError)
                        }
                    }
                }
            }
        } catch (err) {
            if (err instanceof Error && err.name === "AbortError") {
                // 사용자가 중단함
                setStatus("idle")
                return
            }

            const errorMessage = err instanceof Error ? err.message : "알 수 없는 오류"
            setStatus("error")
            setError(errorMessage)
            onError?.(errorMessage)
        }
    }, [agentType, projectId, status, onNodeComplete, onComplete, onError])

    const abort = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            abortControllerRef.current = null
        }
        setStatus("idle")
    }, [])

    return {
        status,
        progress,
        currentNodeId,
        completedNodes,
        message,
        error,
        start,
        abort,
    }
}
