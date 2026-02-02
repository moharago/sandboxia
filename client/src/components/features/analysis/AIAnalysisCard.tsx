"use client"

import { Sparkles } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils/cn"

interface AIAnalysisCardProps {
    title?: string
    summary: string
    recommendation?: string
    confidence?: number
    /** 신뢰도 표시 방식: "numeric" = 숫자%, "category" = 높음/보통/낮음, "hidden" = 숨김 */
    confidenceDisplay?: "numeric" | "category" | "hidden"
}

/**
 * 신뢰도 → 범주형 변환
 *
 * 기준:
 * - 높음: 80% 이상
 * - 보통: 50% ~ 79%
 * - 낮음: 50% 미만
 */
function getConfidenceLabel(confidence: number): { label: string; className: string } {
    if (confidence >= 80) {
        // 80% 이상 → 높음 (녹색)
        return { label: "높음", className: "text-green-700 border-green-300 bg-green-50" }
    } else if (confidence >= 50) {
        // 50~79% → 보통 (주황색)
        return { label: "보통", className: "text-amber-700 border-amber-300 bg-amber-50" }
    } else {
        // 50% 미만 → 낮음 (빨간색)
        return { label: "낮음", className: "text-red-700 border-red-300 bg-red-50" }
    }
}

export function AIAnalysisCard({
    title = "AI 분석 결과",
    summary,
    recommendation,
    confidence,
    confidenceDisplay = "category",
}: AIAnalysisCardProps) {
    const confidenceInfo = confidence !== undefined ? getConfidenceLabel(confidence) : null

    return (
        <Card className="border-primary/30 bg-gradient-to-r from-blue-50/50 to-teal-50/50">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-primary" />
                        <CardTitle>{title}</CardTitle>
                    </div>
                    {confidence !== undefined && confidenceDisplay !== "hidden" && (
                        <Badge
                            variant="outline"
                            className={cn(
                                confidenceDisplay === "category" && confidenceInfo
                                    ? confidenceInfo.className
                                    : "text-primary border-primary"
                            )}
                        >
                            {confidenceDisplay === "numeric"
                                ? `신뢰도 ${confidence}%`
                                : `판단 신뢰도: ${confidenceInfo?.label}`}
                        </Badge>
                    )}
                </div>
                <CardDescription className="text-base mt-2">{summary}</CardDescription>
            </CardHeader>
            {recommendation && (
                <CardContent>
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-white/80 border border-primary/30">
                        <span className="font-medium">
                            AI 추천: <span className="text-amber-600 font-bold">{recommendation}</span>
                        </span>
                    </div>
                </CardContent>
            )}
        </Card>
    )
}
