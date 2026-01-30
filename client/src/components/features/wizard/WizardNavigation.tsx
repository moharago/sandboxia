"use client"

import { Button } from "@/components/ui/button"
import { AlertTriangle, ArrowLeft, ArrowRight, RefreshCw } from "lucide-react"
import type { ReactNode } from "react"

interface WizardNavigationProps {
    /** 이전 단계 버튼 클릭 핸들러 (없으면 이전 버튼 숨김) */
    onBack?: () => void
    /** 이전 버튼 라벨 */
    backLabel?: string

    /** 다음 단계 버튼 클릭 핸들러 (분석 없이 이동) */
    onNext?: () => void
    /** 다음 버튼 라벨 */
    nextLabel?: string

    /** AI 분석 + 다음 단계 핸들러 */
    onAnalyze?: () => void
    /** 분석 버튼 라벨 */
    analyzeLabel?: string

    /** 분석 완료 여부 - true면 [재분석][다음] 버튼, false면 [AI 분석 및 다음] 버튼 */
    isAnalyzed?: boolean

    /** 데이터 변경 여부 - true면 "재분석 권장" 메시지 표시 */
    hasChanges?: boolean

    /** 로딩 상태 (분석 중) */
    isLoading?: boolean

    /** 분석 버튼 비활성화 여부 (폼 유효성 검사 실패 시) */
    isAnalyzeDisabled?: boolean

    /** 추가 버튼 (다운로드 등) - 다음 버튼 왼쪽에 렌더링 */
    extraButtons?: ReactNode
}

export function WizardNavigation({
    onBack,
    backLabel = "이전 단계",
    onNext,
    nextLabel = "다음 단계",
    onAnalyze,
    analyzeLabel = "AI 분석 및 다음 단계",
    isAnalyzed = false,
    hasChanges = false,
    isLoading = false,
    isAnalyzeDisabled = false,
    extraButtons,
}: WizardNavigationProps) {
    return (
        <div className="flex flex-col gap-3">
            {/* 데이터 변경 경고 메시지 */}
            {isAnalyzed && hasChanges && (
                <div className="flex items-center justify-end gap-2 text-sm text-amber-600">
                    <AlertTriangle className="h-4 w-4" />
                    <span>입력 데이터가 변경되었습니다. 재분석을 권장합니다.</span>
                </div>
            )}

            <div className="flex justify-between">
                {/* 왼쪽: 이전 버튼 */}
                {onBack ? (
                    <Button variant="outline" onClick={onBack} disabled={isLoading} className="gap-2">
                        <ArrowLeft className="h-4 w-4" />
                        {backLabel}
                    </Button>
                ) : (
                    <div />
                )}

                {/* 오른쪽: 다음/분석 버튼들 */}
                <div className="flex gap-2">
                    {extraButtons}

                    {isAnalyzed ? (
                        <>
                            {/* 분석 완료 상태: 재분석 + 다음 단계 */}
                            {onAnalyze && (
                                <Button variant="outline" onClick={onAnalyze} disabled={isLoading || isAnalyzeDisabled} className="gap-2">
                                    <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                                    AI 재분석
                                </Button>
                            )}
                            {onNext && (
                                <Button variant="default" onClick={onNext} disabled={isLoading} className="gap-2">
                                    {nextLabel}
                                    <ArrowRight className="h-4 w-4" />
                                </Button>
                            )}
                        </>
                    ) : (
                        /* 분석 전 상태: AI 분석 및 다음 단계 */
                        onAnalyze && (
                            <Button onClick={onAnalyze} disabled={isLoading || isAnalyzeDisabled} className="gap-2">
                                {analyzeLabel}
                                <ArrowRight className="h-4 w-4" />
                            </Button>
                        )
                    )}
                </div>
            </div>
        </div>
    )
}
