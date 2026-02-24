"use client"

import type { NodeInfo } from "@/types/api/agent-progress"
import { Check, Circle, Loader2, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"

interface AILoaderProps {
    /**
     * 페이지별 상세 메시지 (예: "트랙을 추천 중입니다...")
     * 컴포넌트가 자동으로 "AI가 " 접두사를 추가하므로 메시지에 포함하지 마세요.
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

export function AILoader({
    message,
    nodes,
    completedNodes = [],
    currentNodeId,
    progress,
}: AILoaderProps) {
    const hasNodes = nodes && nodes.length > 0

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-white/60 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-4 rounded-lg bg-white p-8 shadow-lg border border-gray-200 min-w-[320px]">
                {/* 스피너 + 아이콘 */}
                <div className="relative">
                    <div className="h-12 w-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
                    <Sparkles className="absolute inset-0 m-auto h-5 w-5 text-primary" />
                </div>

                {/* 제목 + 메시지 */}
                <div className="flex flex-col items-center gap-1">
                    <p className="text-lg font-medium text-foreground">AI 분석 중</p>
                    <p className="text-sm text-muted-foreground">
                        {message ? `AI가 ${message}` : "잠시만 기다려주세요..."}
                    </p>
                </div>

                {/* 진행률 바 */}
                {typeof progress === "number" && (
                    <div className="w-full mt-2">
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary transition-all duration-300 ease-out"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                        <p className="text-xs text-muted-foreground text-center mt-1">
                            {progress}%
                        </p>
                    </div>
                )}

                {/* 노드 체크리스트 */}
                {hasNodes && (
                    <div className="w-full mt-2 space-y-2">
                        {nodes.map((node) => {
                            const isCompleted = completedNodes.includes(node.id)
                            const isRunning = currentNodeId === node.id
                            const isPending = !isCompleted && !isRunning

                            return (
                                <div
                                    key={node.id}
                                    className={cn(
                                        "flex items-center gap-3 px-3 py-2 rounded-md transition-colors",
                                        isCompleted && "bg-green-50",
                                        isRunning && "bg-primary/5",
                                        isPending && "bg-gray-50"
                                    )}
                                >
                                    {/* 상태 아이콘 */}
                                    {isCompleted ? (
                                        <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                                    ) : isRunning ? (
                                        <Loader2 className="h-4 w-4 text-primary animate-spin flex-shrink-0" />
                                    ) : (
                                        <Circle className="h-4 w-4 text-gray-300 flex-shrink-0" />
                                    )}

                                    {/* 노드 라벨 */}
                                    <span
                                        className={cn(
                                            "text-sm",
                                            isCompleted && "text-green-700 font-medium",
                                            isRunning && "text-primary font-medium",
                                            isPending && "text-gray-400"
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
