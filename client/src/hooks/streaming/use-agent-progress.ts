/**
 * Agent Progress SSE Hook
 *
 * 실행 중인 에이전트의 진행 상태를 SSE로 구독하는 훅
 *
 * @example
 * ```tsx
 * const { status, progress, completedNodes, subscribe } = useAgentProgress({
 *   projectId: "uuid-...",
 *   onNodeComplete: (nodeId) => console.log(`${nodeId} 완료`),
 *   onComplete: () => console.log("분석 완료"),
 * })
 *
 * // mutation 실행과 동시에 구독 시작
 * const handleAnalyze = () => {
 *   subscribe()  // SSE 구독 시작
 *   mutation.mutate({ project_id: id })  // 에이전트 실행
 * }
 * ```
 */

import { getAuthToken } from "@/lib/supabase/client"
import { useUIStore } from "@/stores/ui-store"
import type { AgentProgressEvent, NodeInfo, SSEConnectionStatus } from "@/types/api/agent-progress"
import { useCallback, useEffect, useRef, useState } from "react"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""

interface UseAgentProgressOptions {
    /** 프로젝트 ID */
    projectId: string
    /** 노드 완료 시 콜백 */
    onNodeComplete?: (nodeId: string) => void
    /** 에이전트 완료 시 콜백 */
    onComplete?: () => void
    /** 에러 발생 시 콜백 */
    onError?: (error: string) => void
    /** 전역 AI 로더 사용 여부 (true면 자동으로 전역 로더 상태 업데이트) */
    useGlobalLoader?: boolean
    /** 전역 로더에 표시할 메시지 */
    globalLoaderMessage?: string
    /** 전역 로더에 표시할 노드 목록 */
    globalLoaderNodes?: NodeInfo[]
}

interface UseAgentProgressReturn {
    /** 현재 연결 상태 */
    status: SSEConnectionStatus
    /** 현재 진행률 (0-100) */
    progress: number
    /** 현재 진행 중인 노드 ID */
    currentNodeId: string | null
    /** 완료된 노드 ID 목록 */
    completedNodes: string[]
    /** 현재 메시지 */
    message: string | null
    /** 에러 메시지 */
    error: string | null
    /** SSE 구독 시작 */
    subscribe: () => void
    /** SSE 구독 중단 */
    unsubscribe: () => void
    /** 상태 초기화 */
    reset: () => void
}

/**
 * 에이전트 진행 상태 SSE 구독 훅
 */
export function useAgentProgress(options: UseAgentProgressOptions): UseAgentProgressReturn {
    const { projectId, onNodeComplete, onComplete, onError, useGlobalLoader, globalLoaderMessage, globalLoaderNodes } = options

    const [status, setStatus] = useState<SSEConnectionStatus>("idle")
    const [progress, setProgress] = useState(0)
    const [currentNodeId, setCurrentNodeId] = useState<string | null>(null)
    const [completedNodes, setCompletedNodes] = useState<string[]>([])
    const [message, setMessage] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const abortControllerRef = useRef<AbortController | null>(null)

    const reset = useCallback(() => {
        setStatus("idle")
        setProgress(0)
        setCurrentNodeId(null)
        setCompletedNodes([])
        setMessage(null)
        setError(null)
    }, [])

    const subscribe = useCallback(async () => {
        // 이미 구독 중이면 무시
        if (status === "connecting" || status === "connected") {
            console.log("[SSE] 이미 구독 중, 무시")
            return
        }

        console.log("[SSE] 구독 시작:", projectId)

        // 상태 초기화
        reset()
        setStatus("connecting")

        // AbortController 생성 (토큰 확인 전에 생성하여 조기 취소 지원)
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
        }
        abortControllerRef.current = new AbortController()

        // 전역 로더 표시
        if (useGlobalLoader) {
            useUIStore.getState().showGlobalAILoader({
                message: globalLoaderMessage,
                nodes: globalLoaderNodes,
                progress: 0,
                completedNodes: [],
                currentNodeId: null,
            })
        }

        // 인증 토큰 가져오기
        let token: string
        try {
            token = await getAuthToken()
        } catch {
            setStatus("error")
            setError("로그인이 필요합니다.")
            if (useGlobalLoader) {
                useUIStore.getState().hideGlobalAILoader()
            }
            onError?.("로그인이 필요합니다.")
            return
        }

        try {
            // GET SSE 엔드포인트 연결
            const response = await fetch(`${API_BASE}/api/v1/agents/progress/subscribe/${projectId}`, {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                signal: abortControllerRef.current.signal,
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
                throw new Error(errorData.detail || `Request failed: ${response.status}`)
            }

            console.log("[SSE] 연결 성공")
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

                // SSE 이벤트 파싱 (data: {...}\n\n 또는 : heartbeat\n\n)
                const lines = buffer.split("\n\n")
                buffer = lines.pop() || ""

                for (const line of lines) {
                    // heartbeat 무시
                    if (line.startsWith(":")) continue

                    if (line.startsWith("data: ")) {
                        try {
                            const jsonStr = line.slice(6)
                            const event: AgentProgressEvent = JSON.parse(jsonStr)

                            console.log("[SSE] 이벤트 수신:", event.event_type, event.node_id, event.progress)

                            switch (event.event_type) {
                                case "agent_start":
                                    // 새 에이전트 시작 시 상태 초기화
                                    setProgress(0)
                                    setCompletedNodes([])
                                    setCurrentNodeId(null)
                                    setMessage(event.message || "분석을 시작합니다...")
                                    if (useGlobalLoader) {
                                        useUIStore.getState().updateGlobalAILoader({
                                            progress: 0,
                                            completedNodes: [],
                                            currentNodeId: null,
                                        })
                                    }
                                    break

                                case "node_start":
                                    setCurrentNodeId(event.node_id || null)
                                    setProgress(event.progress)
                                    setMessage(event.message || null)
                                    if (useGlobalLoader) {
                                        useUIStore.getState().updateGlobalAILoader({
                                            currentNodeId: event.node_id || null,
                                            progress: event.progress,
                                        })
                                    }
                                    break

                                case "node_end":
                                    setCompletedNodes(event.completed_nodes)
                                    setCurrentNodeId(null) // 노드 완료 후 currentNodeId 초기화 → AILoader에서 다음 미완료 노드를 자동 판단
                                    setProgress(event.progress)
                                    setMessage(event.message || null)
                                    if (useGlobalLoader) {
                                        useUIStore.getState().updateGlobalAILoader({
                                            completedNodes: event.completed_nodes,
                                            currentNodeId: null,
                                            progress: event.progress,
                                        })
                                    }
                                    if (event.node_id) {
                                        onNodeComplete?.(event.node_id)
                                    }
                                    break

                                case "agent_end":
                                    setStatus("completed")
                                    setProgress(100)
                                    setCurrentNodeId(null)
                                    setMessage(event.message || "분석이 완료되었습니다.")
                                    // 전역 로더는 숨기지 않음 - 페이지 전환 후 명시적으로 숨겨야 함
                                    if (useGlobalLoader) {
                                        useUIStore.getState().updateGlobalAILoader({ progress: 100 })
                                    }
                                    onComplete?.()
                                    return // 스트림 종료

                                case "error":
                                    setStatus("error")
                                    setError(event.message || "오류가 발생했습니다.")
                                    if (useGlobalLoader) {
                                        useUIStore.getState().hideGlobalAILoader()
                                    }
                                    onError?.(event.message || "오류가 발생했습니다.")
                                    return // 스트림 종료
                            }
                        } catch (parseError) {
                            console.error("SSE 파싱 오류:", parseError)
                        }
                    }
                }
            }

            // SSE 스트림이 agent_end/error 이벤트 없이 종료된 경우 cleanup
            // (done=true로 루프 탈출했으나 return되지 않은 경우)
            console.log("[SSE] 스트림 종료 (done=true)")
            setStatus("idle")
            setCurrentNodeId(null)
            setMessage(null)
            if (useGlobalLoader) {
                useUIStore.getState().hideGlobalAILoader()
            }
        } catch (err) {
            if (err instanceof Error && err.name === "AbortError") {
                // 사용자가 중단함
                setStatus("idle")
                if (useGlobalLoader) {
                    useUIStore.getState().hideGlobalAILoader()
                }
                return
            }

            const errorMessage = err instanceof Error ? err.message : "알 수 없는 오류"
            setStatus("error")
            setError(errorMessage)
            if (useGlobalLoader) {
                useUIStore.getState().hideGlobalAILoader()
            }
            onError?.(errorMessage)
        }
    }, [projectId, status, reset, onNodeComplete, onComplete, onError, useGlobalLoader, globalLoaderMessage, globalLoaderNodes])

    const unsubscribe = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            abortControllerRef.current = null
        }
        setStatus("idle")
    }, [])

    // 컴포넌트 언마운트 시 자동 cleanup
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort()
                abortControllerRef.current = null
            }
        }
    }, [])

    return {
        status,
        progress,
        currentNodeId,
        completedNodes,
        message,
        error,
        subscribe,
        unsubscribe,
        reset,
    }
}
