"use client"

import { cn } from "@/lib/utils/cn"
import type { NodeInfo } from "@/types/api/agent-progress"
import { Check, Circle, Loader2, Sparkles } from "lucide-react"

interface AILoaderProps {
    /**
     * 페이지별 상세 메시지 (예: "트랙을 추천 중입니다...")
     * 컴포넌트는 메시지를 그대로 렌더링합니다 (자동으로 접두사를 추가하지 않음).
     */
    message?: string
    /**
     * 노드 목록 (체크리스트로 표시)
     */
    nodes?: NodeInfo[]
    /**
     * 완료된 노드 ID 목록
     */
    completedNodes?: string[]
    /**
     * 현재 진행 중인 노드 ID
     */
    currentNodeId?: string | null
    /**
     * 진행률 (0-100)
     */
    progress?: number
}

export function AILoader({ message, nodes, completedNodes = [], currentNodeId, progress }: AILoaderProps) {
    const hasNodes = nodes && nodes.length > 0

    // 진행 중인 노드 자동 판단: currentNodeId가 없으면 완료되지 않은 첫 번째 노드를 진행 중으로 표시
    const runningNodeId = currentNodeId ?? (hasNodes ? nodes.find((n) => !completedNodes.includes(n.id))?.id : null)

    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-white/60 backdrop-blur-sm"
            role="status"
            aria-live="polite"
            aria-busy={true}
            aria-label={message || "AI 분석 중"}
        >
            <div className="flex flex-col items-center gap-4 rounded-lg bg-white p-8 shadow-lg border border-gray-200 min-w-[320px]">
                <div className="flex flex-col items-center gap-1">
                    <Sparkles className="text-primary w-5 h-5 animate-pulse" />
                    <p className="text-lg font-medium mt-2 text-foreground">
                        <span>AI 분석 중</span>
                    </p>
                    <p className="text-sm text-muted-foreground">{message ? `${message}` : "잠시만 기다려주세요..."}</p>
                </div>

                {/* 진행률 바 */}
                {typeof progress === "number" && (() => {
                    const normalizedProgress = Math.min(100, Math.max(0, Number(progress) || 0))
                    return (
                        <div className="w-full mt-2">
                            <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-primary transition-all duration-300 ease-out" style={{ width: `${normalizedProgress}%` }} />
                            </div>
                            <p className="text-xs text-muted-foreground text-center mt-1">{normalizedProgress}%</p>
                        </div>
                    )
                })()}

                {/* 노드 체크리스트 */}
                {hasNodes && (
                    <div className="w-full mt-2">
                        {nodes.map((node) => {
                            const isCompleted = completedNodes.includes(node.id)
                            const isRunning = runningNodeId === node.id
                            const isPending = !isCompleted && !isRunning

                            return (
                                <div key={node.id} className="flex items-center gap-2 px-2 py-1">
                                    {/* 상태 아이콘 - 모두 동일한 크기(h-4 w-4)로 통일 */}
                                    {isCompleted ? (
                                        <Check className="h-4 w-4 text-primary flex-shrink-0" />
                                    ) : isRunning ? (
                                        <Loader2 className="h-4 w-4 text-primary animate-spin flex-shrink-0" />
                                    ) : (
                                        <Circle className="h-4 w-4 text-gray-300 flex-shrink-0" />
                                    )}

                                    {/* 노드 라벨 */}
                                    <span
                                        className={cn(
                                            "text-sm",
                                            isCompleted && "text-primary font-medium",
                                            isRunning && "text-primary font-medium",
                                            isPending && "text-gray-400 font-medium"
                                        )}
                                    >
                                        {node.label}
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
