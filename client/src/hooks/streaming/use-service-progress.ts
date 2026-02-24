/**
 * Service Structurer Progress SSE Hook
 *
 * 서비스 구조화 에이전트의 진행 상태를 SSE로 수신하는 훅
 * (파일 업로드가 필요하므로 별도 훅으로 분리)
 *
 * @example
 * ```tsx
 * const { status, progress, completedNodes, start } = useServiceProgress({
 *   sessionId: "uuid-...",
 *   requestedTrack: "quick_check",
 *   consultantInput: { company_name: "...", ... },
 *   files: [file1, file2],
 *   onComplete: () => console.log("분석 완료"),
 * })
 *
 * // 분석 시작
 * <button onClick={start}>분석 시작</button>
 * ```
 */

import { useAuthStore } from "@/stores/auth-store"
import type {
    AgentProgressEvent,
    SSEConnectionStatus,
    UseAgentProgressReturn,
} from "@/types/api/agent-progress"
import { useCallback, useRef, useState } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""

interface UseServiceProgressOptions {
    /** 세션(프로젝트) ID */
    sessionId: string
    /** 트랙 (counseling/quick_check/temp_permit/demo) */
    requestedTrack: string
    /** 컨설턴트 입력 데이터 */
    consultantInput: Record<string, unknown>
    /** 업로드할 파일 목록 */
    files: File[]
    /** 노드 완료 시 콜백 */
    onNodeComplete?: (nodeId: string) => void
    /** 에이전트 완료 시 콜백 */
    onComplete?: () => void
    /** 에러 발생 시 콜백 */
    onError?: (error: string) => void
}

/**
 * 서비스 구조화 진행 상태 SSE 훅
 */
export function useServiceProgress(
    options: UseServiceProgressOptions
): UseAgentProgressReturn {
    const {
        sessionId,
        requestedTrack,
        consultantInput,
        files,
        onNodeComplete,
        onComplete,
        onError,
    } = options

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
            // FormData 구성
            const formData = new FormData()
            formData.append("session_id", sessionId)
            formData.append("requested_track", requestedTrack)
            formData.append("consultant_input", JSON.stringify(consultantInput))

            for (const file of files) {
                formData.append("files", file)
            }

            const response = await fetch(
                `${API_BASE}/api/v1/agents/progress/stream/service`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                    body: formData,
                    signal: abortControllerRef.current.signal,
                }
            )

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
                buffer = lines.pop() || ""

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const jsonStr = line.slice(6)
                            const event: AgentProgressEvent = JSON.parse(jsonStr)

                            switch (event.event_type) {
                                case "agent_start":
                                    setMessage(event.message || "서비스 분석을 시작합니다...")
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
                                    setMessage(event.message || "서비스 분석이 완료되었습니다.")
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
                setStatus("idle")
                return
            }

            const errorMessage = err instanceof Error ? err.message : "알 수 없는 오류"
            setStatus("error")
            setError(errorMessage)
            onError?.(errorMessage)
        }
    }, [
        sessionId,
        requestedTrack,
        consultantInput,
        files,
        status,
        onNodeComplete,
        onComplete,
        onError,
    ])

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
