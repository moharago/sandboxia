"use client"

import { use, useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { CheckCircle2, XCircle, AlertCircle, Info } from "lucide-react"
import { WizardNavigation } from "@/components/features/wizard"
import { ReferencePanel, type CaseData } from "@/components/features/draft/ReferencePanel"
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { tracks } from "@/data"
import { useUIStore } from "@/stores/ui-store"
import { useWizardStore } from "@/stores/wizard-store"
import { useTrackRecommendMutation, useTrackSelectMutation } from "@/hooks/mutations/use-track-mutation"
import { useTrackQuery } from "@/hooks/queries/use-track-query"
import { cn } from "@/lib/utils/cn"
import type { RecommendableTrack, TrackComparisonItem, TrackRecommendResponse } from "@/types/api/track"

interface TrackPageProps {
    params: Promise<{ id: string }>
}

// API 트랙 ID → UI 트랙 ID 매핑
const API_TO_UI_TRACK: Record<RecommendableTrack, string> = {
    demo: "track-demonstration",
    temp_permit: "track-temporary",
    quick_check: "track-fastcheck",
}

// UI 트랙 ID → API 트랙 ID 매핑
const UI_TO_API_TRACK: Record<string, RecommendableTrack> = {
    "track-demonstration": "demo",
    "track-temporary": "temp_permit",
    "track-fastcheck": "quick_check",
}

const verdictStyles: Record<string, { bg: string; text: string; border: string }> = {
    "AI 추천": {
        bg: "bg-blue-50",
        text: "text-blue-700",
        border: "border-blue-200",
    },
    "조건부 가능": {
        bg: "bg-amber-50",
        text: "text-amber-700",
        border: "border-amber-200",
    },
    비추천: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
}

// API 응답을 UI 형식으로 변환
function transformApiResponse(response: TrackRecommendResponse) {
    const recommendations: Array<{
        trackId: string
        rank: number
        score: number
        verdict: string
        reasons: Array<{ type: "positive" | "negative" | "neutral"; text: string; source: string; description: string }>
    }> = []

    // 3개 트랙을 순회하며 UI 형식으로 변환
    const trackKeys: RecommendableTrack[] = ["demo", "temp_permit", "quick_check"]

    for (const apiTrackId of trackKeys) {
        const trackData = response.track_comparison[apiTrackId] as TrackComparisonItem | undefined
        if (!trackData) continue

        const uiTrackId = API_TO_UI_TRACK[apiTrackId]

        // reasons와 evidence를 1:1 매핑 (서버 프롬프트에서 reasons[i]와 evidence[i]가 대응)
        const reasons = trackData.reasons.map((r, index) => {
            const evidence = trackData.evidence?.[index]
            return {
                type: r.type,
                text: r.text,
                source: evidence ? evidence.source : "",
                description: evidence?.description ?? "",
            }
        })

        recommendations.push({
            trackId: uiTrackId,
            rank: trackData.rank,
            score: trackData.fit_score,
            verdict: trackData.status,
            reasons,
        })
    }

    return {
        confidence: response.confidence_score,
        summary: response.result_summary,
        recommendations: recommendations.sort((a, b) => a.rank - b.rank),
    }
}

// track_comparison evidence에서 사례 데이터 추출
function extractCasesFromEvidence(response: TrackRecommendResponse): CaseData[] {
    const seen = new Set<string>()
    const cases: CaseData[] = []

    const trackKeys: RecommendableTrack[] = ["demo", "temp_permit", "quick_check"]

    for (const key of trackKeys) {
        const trackData = response.track_comparison[key]
        if (!trackData) continue

        for (const ev of trackData.evidence) {
            if (ev.source_type !== "사례") continue
            if (!ev.service_name) continue

            const id = ev.source || ev.service_name
            if (seen.has(id)) continue
            seen.add(id)

            // ev.source (case_id)에서 사례명 추출: "실증특례_162_위비케어 컨소시엄" → "위비케어 컨소시엄"
            let caseName = ev.company_name || ""
            if (ev.source) {
                const parts = ev.source.split("_")
                if (parts.length >= 3) {
                    caseName = parts.slice(2).join("_")  // 3번째 이후 부분을 사례명으로 사용
                }
            }

            cases.push({
                id,
                title: ev.service_name,
                company: caseName,
                track: ev.track || "",
                summary: ev.description || "",
                relevance: ev.similarity,
                link: ev.source_url || undefined,
            })
        }
    }

    return cases
}

export default function TrackPage({ params }: TrackPageProps) {
    const { id } = use(params)
    const router = useRouter()

    const { setTrackSelection, markStepComplete, setCurrentStep } = useWizardStore()
    const { devIsAnalyzed, devHasChanges } = useUIStore()

    const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null)
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)

    // Supabase에서 트랙 추천 결과 조회
    const { data: trackResult, isLoading: isLoadingTrack } = useTrackQuery(id)

    // 결과 변환
    const analysisResult = trackResult ? transformApiResponse(trackResult) : null
    const defaultTrackId = trackResult ? API_TO_UI_TRACK[trackResult.recommended_track] : null

    // evidence에서 사례 데이터 추출
    const evidenceCases = useMemo(() => {
        if (!trackResult) return []
        return extractCasesFromEvidence(trackResult)
    }, [trackResult])

    // AI 추천 트랙을 기본 선택으로 (사용자가 아직 선택하지 않은 경우)
    const effectiveSelectedTrackId = selectedTrackId ?? defaultTrackId

    // API Mutations
    const recommendMutation = useTrackRecommendMutation({
        onError: (error) => {
            console.error("트랙 추천 실패:", error)
        },
    })

    const selectMutation = useTrackSelectMutation({
        onSuccess: () => {
            markStepComplete(3)
            setCurrentStep(4)
            router.push(`/projects/${id}/draft`)
        },
        onError: (error) => {
            console.error("트랙 저장 실패:", error)
        },
    })

    const handleSelectTrack = (trackId: string) => {
        setSelectedTrackId(trackId)
        const track = tracks.find((t) => t.id === trackId)
        if (track) {
            setTrackSelection(track)
        }
    }

    const handleBack = () => {
        setCurrentStep(2)
        router.push(`/projects/${id}/eligibility`)
    }

    const handleSave = async () => {
        if (!effectiveSelectedTrackId) return

        const apiTrackId = UI_TO_API_TRACK[effectiveSelectedTrackId]
        if (!apiTrackId) return

        const track = tracks.find((t) => t.id === effectiveSelectedTrackId)
        if (track) {
            setTrackSelection(track)
        }

        selectMutation.mutate({
            projectId: id,
            track: apiTrackId,
        })
    }

    const getReasonIcon = (type: string) => {
        switch (type) {
            case "positive":
                return <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
            case "negative":
                return <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
            case "neutral":
                return <AlertCircle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
            default:
                return null
        }
    }

    const isAnalyzing = recommendMutation.isPending
    const isSaving = selectMutation.isPending
    const isError = recommendMutation.isError

    // 데이터 로딩 중
    if (isLoadingTrack) {
        return <AILoadingOverlay message="이전 분석 결과를 확인하고 있습니다..." />
    }

    // AI 분석 중 (재분석 시에만 해당)
    if (isAnalyzing) {
        return <AILoadingOverlay message="AI 트랙 추천 중" />
    }

    // 에러
    if (isError) {
        return (
            <div className="py-6">
                <div className="container">
                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="text-center space-y-4">
                            <XCircle className="h-12 w-12 mx-auto text-red-500" />
                            <h2 className="text-lg font-semibold">트랙 분석에 실패했습니다</h2>
                            <p className="text-muted-foreground">{recommendMutation.error?.message || "알 수 없는 오류가 발생했습니다."}</p>
                            <button
                                type="button"
                                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
                                onClick={() => router.push(`/projects/${id}/eligibility`)}
                            >
                                이전 단계로 돌아가기
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // 결과 없음 - 이전 단계에서 트랙 추천이 실행되지 않은 경우
    if (!analysisResult) {
        return (
            <div className="py-6">
                <div className="container">
                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="text-center space-y-4">
                            <AlertCircle className="h-12 w-12 mx-auto text-amber-500" />
                            <h2 className="text-lg font-semibold">트랙 추천 결과가 없습니다</h2>
                            <p className="text-muted-foreground">이전 단계(시장출시 진단)에서 &quot;다음 단계&quot;를 눌러 진행해주세요.</p>
                            <button
                                type="button"
                                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
                                onClick={() => router.push(`/projects/${id}/eligibility`)}
                            >
                                이전 단계로 돌아가기
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    const sortedRecommendations = analysisResult.recommendations

    return (
        <TooltipProvider>
            <div className="py-6">
                {isSaving && <AILoadingOverlay message="트랙 선택을 저장하고 있습니다..." />}
                <div className="container">
                    <div className="flex gap-4">
                        {/* 왼쪽: 메인 콘텐츠 */}
                        <div className={isReferencePanelOpen ? "flex-[2] space-y-6" : "flex-1 space-y-6"}>
                            <div>
                                <h1 className="text-2xl font-bold mb-2">트랙 선택</h1>
                                <p className="text-muted-foreground">AI가 분석한 결과를 바탕으로 최적의 규제 샌드박스 트랙을 선택하세요</p>
                            </div>

                            {/* AI 분석 요약 */}
                            <AIAnalysisCard summary={analysisResult.summary} confidence={analysisResult.confidence} />

                            {/* 트랙 카드들 */}
                            <div className="space-y-4">
                                {sortedRecommendations.map((rec) => {
                                    const track = tracks.find((t) => t.id === rec.trackId)
                                    if (!track) return null

                                    const isSelected = effectiveSelectedTrackId === track.id
                                    const style = verdictStyles[rec.verdict] || verdictStyles["비추천"]

                                    return (
                                        <Card
                                            key={track.id}
                                            className={cn("relative overflow-hidden transition-all cursor-pointer", isSelected && "ring-2 ring-primary")}
                                            onClick={() => handleSelectTrack(track.id)}
                                        >
                                            <CardHeader className="pb-3">
                                                <div className="flex items-start justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <div
                                                            className={cn(
                                                                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                                                                isSelected ? "bg-primary text-white" : "bg-muted text-muted-foreground"
                                                            )}
                                                        >
                                                            {rec.rank}
                                                        </div>
                                                        <div className="flex items-center gap-1.5">
                                                            <h3 className="text-lg font-semibold">{track.name}</h3>
                                                            <Tooltip>
                                                                <TooltipTrigger asChild>
                                                                    <button
                                                                        type="button"
                                                                        aria-label="트랙 정보"
                                                                        className="text-muted-foreground hover:text-foreground transition-colors"
                                                                        onClick={(e) => e.stopPropagation()}
                                                                    >
                                                                        <Info className="h-4 w-4" />
                                                                    </button>
                                                                </TooltipTrigger>
                                                                <TooltipContent side="right" sideOffset={8} className="max-w-sm text-left">
                                                                    <div className="space-y-2">
                                                                        <p>{track.description}</p>
                                                                        <p className="text-muted-foreground">
                                                                            <span className="font-medium text-foreground">소요 기간:</span> {track.duration}
                                                                        </p>
                                                                        <div>
                                                                            <span className="font-medium">주요 요건:</span>
                                                                            <ul className="mt-1 space-y-0.5 text-muted-foreground">
                                                                                {track.requirements.slice(0, 4).map((req, i) => (
                                                                                    <li key={i}>• {req}</li>
                                                                                ))}
                                                                            </ul>
                                                                        </div>
                                                                    </div>
                                                                </TooltipContent>
                                                            </Tooltip>
                                                        </div>
                                                    </div>
                                                    <Badge variant="outline" className={cn(style.bg, style.text, style.border)}>
                                                        {rec.verdict}
                                                    </Badge>
                                                </div>
                                            </CardHeader>

                                            <div className="mx-6 border-t border-gray-200" />

                                            <CardContent className="space-y-4 mt-3">
                                                {/* AI 분석 결과 */}
                                                <div className="space-y-2">
                                                    <ul className="space-y-2">
                                                        {rec.reasons.map((reason, index) => (
                                                            <li key={index} className="flex items-start gap-2 text-sm">
                                                                {getReasonIcon(reason.type)}
                                                                <div className="flex-1">
                                                                    <p className="text-foreground">{reason.text}</p>
                                                                    {reason.source && <p className="text-muted-foreground/70 mt-1">근거: {reason.source}{reason.description ? ` - ${reason.description}` : ""}</p>}
                                                                </div>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )
                                })}
                            </div>

                            <WizardNavigation
                                onBack={handleBack}
                                onAnalyze={handleSave}
                                onNext={() => {
                                    if (!effectiveSelectedTrackId) return
                                    const track = tracks.find((t) => t.id === effectiveSelectedTrackId)
                                    if (track) {
                                        setTrackSelection(track)
                                        markStepComplete(3)
                                        setCurrentStep(4)
                                        router.push(`/projects/${id}/draft`)
                                    }
                                }}
                                analyzeLabel="저장 및 다음 단계"
                                nextLabel="다음 단계"
                                isAnalyzed={!!analysisResult}
                                hasChanges={devHasChanges}
                                isLoading={isSaving}
                                isAnalyzeDisabled={!effectiveSelectedTrackId}
                            />
                        </div>

                        {/* 오른쪽: 참고 패널 */}
                        <div className={isReferencePanelOpen ? "flex-1" : ""}>
                            <div className="sticky top-16">
                                <ReferencePanel isOpen={isReferencePanelOpen} onToggle={() => setIsReferencePanelOpen(!isReferencePanelOpen)} cases={evidenceCases.length > 0 ? evidenceCases : undefined} />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </TooltipProvider>
    )
}
