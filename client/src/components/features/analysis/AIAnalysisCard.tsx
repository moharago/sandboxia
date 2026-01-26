"use client"

import { Sparkles } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface AIAnalysisCardProps {
    summary: string
    recommendation?: string
    confidence?: number
}

export function AIAnalysisCard({ summary, recommendation, confidence }: AIAnalysisCardProps) {
    return (
        <Card className="border-primary/30 bg-gradient-to-r from-blue-50/50 to-teal-50/50">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-primary" />
                        <CardTitle>AI 분석 결과</CardTitle>
                    </div>
                    {confidence !== undefined && (
                        <Badge variant="outline" className="text-primary border-primary">
                            신뢰도 {confidence}%
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
