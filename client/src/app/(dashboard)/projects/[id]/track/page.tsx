"use client"

import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import type { CaseData } from "@/components/features/draft/ReferencePanel"
import { WizardNavigation } from "@/components/features/wizard/WizardNavigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ConfirmModal } from "@/components/ui/confirm-modal"
import { NoResultsView } from "@/components/ui/no-results-view"
import { PageLoader } from "@/components/ui/page-loader"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { tracks } from "@/data"
import { useDraftGenerateMutation } from "@/hooks/mutations/use-draft-mutation"
import { useTrackRecommendMutation, useTrackSelectMutation } from "@/hooks/mutations/use-track-mutation"
import { useAgentNodesQuery } from "@/hooks/queries/use-agent-nodes-query"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"
import { useTrackQuery } from "@/hooks/queries/use-track-query"
import { useAgentProgress } from "@/hooks/streaming/use-agent-progress"
import { cn } from "@/lib/utils/cn"
import { getStepPagePath, PAGE_STEPS } from "@/lib/utils/step-utils"
import { useUIStore } from "@/stores/ui-store"
import { useWizardStore } from "@/stores/wizard-store"
import type { Regulation } from "@/types/api/eligibility"
import type { RecommendableTrack, TrackComparisonItem, TrackRecommendResponse } from "@/types/api/track"
import { useQueryClient } from "@tanstack/react-query"
import { AlertCircle, CheckCircle2, ExternalLink, Info, XCircle } from "lucide-react"
import dynamic from "next/dynamic"
import { useRouter } from "next/navigation"
import { use, useEffect, useMemo, useRef, useState } from "react"

// async-suspense-boundaries: ReferencePanel lazy loading
const ReferencePanel = dynamic(() => import("@/components/features/draft/ReferencePanel").then((mod) => mod.ReferencePanel), { ssr: false })

interface TrackPageProps {
    params: Promise<{ id: string }>
}

const API_TO_UI_TRACK: Record<RecommendableTrack, string> = {
    demo: "track-demonstration",
    temp_permit: "track-temporary",
    quick_check: "track-fastcheck",
}

const UI_TO_API_TRACK: Record<string, RecommendableTrack> = {
    "track-demonstration": "demo",
    "track-temporary": "temp_permit",
    "track-fastcheck": "quick_check",
}

const verdictStyles: Record<string, { bg: string; text: string; border: string }> = {
    "AI 추천": { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
    "조건부 가능": { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
    비추천: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
}

function transformApiResponse(response: TrackRecommendResponse) {
    const recommendations: Array<{
        trackId: string
        rank: number
        score: number
        verdict: string
        reasons: Array<{ type: "positive" | "negative" | "neutral"; text: string; source: string; sourceUrl?: string; description: string }>
    }> = []

    const trackKeys: RecommendableTrack[] = ["demo", "temp_permit", "quick_check"]

    for (const apiTrackId of trackKeys) {
        const trackData = response.track_comparison[apiTrackId] as TrackComparisonItem | undefined
        if (!trackData) continue

        const uiTrackId = API_TO_UI_TRACK[apiTrackId]
        const reasons = trackData.reasons.map((r, index) => {
            const evidence = trackData.evidence?.[index]
            return {
                type: r.type,
                text: r.text,
                source: evidence ? evidence.source : "",
                sourceUrl: evidence?.source_url || undefined,
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

function transformSimilarCases(response: TrackRecommendResponse): CaseData[] {
    if (!response.similar_cases || !Array.isArray(response.similar_cases) || response.similar_cases.length === 0) return []

    return response.similar_cases.map((c, idx) => ({
        id: `case-${idx}`,
        title: c.title,
        company: c.company,
        track: c.track,
        summary: c.summary,
        relevance: c.similarity,
        link: c.source_url || undefined,
    }))
}

const PAGE_STEP = PAGE_STEPS.track // 3

export default function TrackPage({ params }: TrackPageProps) {
    const { id } = use(params)
    const router = useRouter()
    const queryClient = useQueryClient()

    const { setTrackSelection, markStepComplete, setCurrentStep } = useWizardStore()
    const { showGlobalAILoader, hideGlobalAILoader } = useUIStore()

    const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null)
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)
    const [isRunningDraftAgent, setIsRunningDraftAgent] = useState(false)

    // 모달 상태
    const [reanalyzeModalOpen, setReanalyzeModalOpen] = useState(false)
    const [staleDataModalOpen, setStaleDataModalOpen] = useState(false) // 이전 단계 재분석으로 인한 재분석 필요 모달

    // 프로젝트 정보 조회 (refetchOnMount: "always"로 자동 refetch)
    const { data: project, isPending: isLoadingProject, isFetching: isFetchingProject } = useProjectQuery(id)
    const { data: trackResult, isPending: isLoadingTrack, isFetching: isFetchingTrack } = useTrackQuery(id)

    const { data: trackNodes } = useAgentNodesQuery("track_recommender")
    const { data: draftNodes } = useAgentNodesQuery("application_drafter")

    // 컴포넌트 마운트 시 전역 로더 숨기기
    useEffect(() => {
        hideGlobalAILoader()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // SSE 진행 상태 (전역 로더 자동 업데이트)
    const trackProgress = useAgentProgress({
        projectId: id,
        useGlobalLoader: true,
        globalLoaderMessage: "최적의 트랙 추천 중...",
        globalLoaderNodes: trackNodes?.nodes,
        onComplete: () => queryClient.invalidateQueries({ queryKey: ["track"] }),
    })
    const draftProgress = useAgentProgress({
        projectId: id,
        useGlobalLoader: true,
        globalLoaderMessage: "신청서 초안 생성 중...",
        globalLoaderNodes: draftNodes?.nodes,
        onComplete: () => queryClient.invalidateQueries({ queryKey: ["draft"] }),
    })

    // 현재 단계와 페이지 단계 비교
    const currentStep = project?.current_step ?? 1
    const isAheadOfCurrentStep = currentStep > PAGE_STEP
    const isAtCurrentStep = currentStep === PAGE_STEP
    const isBehindCurrentStep = currentStep < PAGE_STEP

    // 기존 결과 확인
    const hasExistingResult = !!trackResult

    // current_step < PAGE_STEP이고 기존 데이터가 있는 경우 재분석 필요 모달 표시
    // isLoading(초기 로드)을 사용하여 background refetch로 인한 모달 재오픈 방지
    const staleModalOpenedRef = useRef(false)
    useEffect(() => {
        if (!isLoadingTrack && !isLoadingProject && isBehindCurrentStep && hasExistingResult && !staleModalOpenedRef.current) {
            staleModalOpenedRef.current = true
            setStaleDataModalOpen(true)
        }
    }, [isLoadingTrack, isLoadingProject, isBehindCurrentStep, hasExistingResult])

    // 결과 변환
    const analysisResult = trackResult ? transformApiResponse(trackResult) : null
    const defaultTrackId = trackResult ? API_TO_UI_TRACK[trackResult.recommended_track] : null

    const referenceCases = useMemo(() => {
        if (!trackResult) return []
        return transformSimilarCases(trackResult)
    }, [trackResult])

    const referenceRegulations = useMemo(() => {
        if (!trackResult?.domain_constraints || !Array.isArray(trackResult.domain_constraints)) return []
        return trackResult.domain_constraints as Regulation[]
    }, [trackResult])

    const effectiveSelectedTrackId = selectedTrackId ?? defaultTrackId
    const hasExistingDraft = !isLoadingProject && Boolean(project?.application_draft && Object.keys(project.application_draft).length > 0)

    // Mutations
    const recommendMutation = useTrackRecommendMutation({
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["track"] }),
        onError: (error) => console.error("트랙 추천 실패:", error),
    })

    const draftMutation = useDraftGenerateMutation()

    const selectMutation = useTrackSelectMutation({
        onError: (error) => console.error("트랙 저장 실패:", error),
    })

    const handleSelectTrack = (trackId: string) => {
        setSelectedTrackId(trackId)
        const track = tracks.find((t) => t.id === trackId)
        if (track) setTrackSelection(track)
    }

    const handleBack = () => {
        setCurrentStep(2)
        router.push(`/projects/${id}/eligibility`)
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

    // 트랙 재분석만 실행 (페이지 이동 없음)
    const runTrackOnly = () => {
        setReanalyzeModalOpen(false)
        trackProgress.subscribe()
        recommendMutation.mutate(
            { project_id: id },
            {
                onSuccess: () => {
                    trackProgress.unsubscribe()
                    hideGlobalAILoader() // 재분석 완료 시 로더 숨김
                },
                onError: () => {
                    trackProgress.unsubscribe()
                    hideGlobalAILoader()
                },
            }
        )
    }

    // 초안 생성 후 이동
    const runDraftAndNavigate = async () => {
        if (!effectiveSelectedTrackId) return
        const apiTrackId = UI_TO_API_TRACK[effectiveSelectedTrackId]
        if (!apiTrackId) return

        const track = tracks.find((t) => t.id === effectiveSelectedTrackId)
        if (track) setTrackSelection(track)

        setIsRunningDraftAgent(true)
        // 전역 로더 표시
        showGlobalAILoader({
            message: "신청서 초안 생성 중...",
            nodes: draftNodes?.nodes,
            progress: 0,
            completedNodes: [],
            currentNodeId: null,
        })
        draftProgress.subscribe()

        selectMutation.mutate(
            { projectId: id, track: apiTrackId },
            {
                onSuccess: async () => {
                    // invalidateQueries는 await 불필요 (백그라운드 실행)
                    queryClient.invalidateQueries({ queryKey: ["projects"] })
                    try {
                        await draftMutation.mutateAsync({ project_id: id })
                    } catch (error) {
                        console.error("신청서 초안 생성 실패:", error)
                        draftProgress.unsubscribe()
                        hideGlobalAILoader()
                        setIsRunningDraftAgent(false)
                        return
                    }
                    // invalidateQueries는 await 불필요 (백그라운드 실행)
                    queryClient.invalidateQueries({ queryKey: ["draft"] })
                    queryClient.invalidateQueries({ queryKey: ["projects"] })
                    markStepComplete(3)
                    setCurrentStep(4)
                    // 전역 로더는 다음 페이지에서 숨김
                    router.push(`/projects/${id}/draft`)
                },
                onError: (error) => {
                    console.error("트랙 저장 실패:", error)
                    hideGlobalAILoader()
                    setIsRunningDraftAgent(false)
                    draftProgress.unsubscribe()
                },
            }
        )
    }

    // 다음 페이지로 이동만 (분석 없이)
    const navigateToNext = () => {
        if (!effectiveSelectedTrackId) return
        const apiTrackId = UI_TO_API_TRACK[effectiveSelectedTrackId]
        if (!apiTrackId) return

        const track = tracks.find((t) => t.id === effectiveSelectedTrackId)
        if (track) setTrackSelection(track)

        // 트랙 선택만 저장하고 이동
        selectMutation.mutate(
            { projectId: id, track: apiTrackId },
            {
                onSuccess: () => {
                    // invalidateQueries는 await 불필요 (백그라운드 실행)
                    queryClient.invalidateQueries({ queryKey: ["projects"] })
                    markStepComplete(3)
                    setCurrentStep(4)
                    router.push(`/projects/${id}/draft`)
                },
            }
        )
    }

    // 재분석 버튼 클릭
    const handleReanalyze = () => {
        setReanalyzeModalOpen(true)
    }

    // 다음 단계 버튼 클릭 (current_step > PAGE_STEP인 경우: 분석 없이 이동만)
    const handleNext = () => {
        if (isAheadOfCurrentStep) {
            // current_step > PAGE_STEP: 분석 없이 바로 이동
            navigateToNext()
        } else {
            // current_step == PAGE_STEP: 초안 생성 후 이동
            runDraftAndNavigate()
        }
    }

    const isAnalyzing = recommendMutation.isPending
    const isSaving = selectMutation.isPending || isRunningDraftAgent

    // 로딩 중
    if (isLoadingTrack || isLoadingProject) {
        return <PageLoader className="flex-1" />
    }

    // current_step < page_step이고 기존 데이터가 없는 경우: "분석 결과가 없습니다" 표시
    if (isBehindCurrentStep && !hasExistingResult) {
        return <NoResultsView onNavigate={() => router.push(getStepPagePath(id, currentStep))} />
    }

    // AI 분석 중 (전역 로더가 표시됨)
    if (isAnalyzing) {
        return <PageLoader className="flex-1" />
    }

    // 에러
    if (recommendMutation.isError) {
        return (
            <div className="py-6">
                <div className="container">
                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="text-center space-y-4">
                            <XCircle className="h-12 w-12 mx-auto text-red-500" />
                            <h2 className="text-lg font-semibold">트랙 분석에 실패했습니다</h2>
                            <p className="text-muted-foreground">{recommendMutation.error?.message || "알 수 없는 오류"}</p>
                            <Button onClick={() => router.push(`/projects/${id}/eligibility`)}>이전 단계로 돌아가기</Button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // 결과 없음
    if (!analysisResult) {
        return <NoResultsView onNavigate={() => router.push(getStepPagePath(id, currentStep))} />
    }

    return (
        <TooltipProvider>
            <div className="py-6">
                {/* 재분석 확인 모달 */}
                <ConfirmModal
                    isOpen={reanalyzeModalOpen}
                    onClose={() => setReanalyzeModalOpen(false)}
                    onConfirm={runTrackOnly}
                    title="트랙 추천 재분석"
                    description={[
                        "이미 트랙 추천이 완료된 상태입니다.",
                        "다시 분석하시겠습니까?",
                        hasExistingDraft
                            ? "기존 분석 결과는 새로운 결과로 대체되며, 신청서 초안도 재생성이 필요합니다."
                            : "기존 분석 결과는 새로운 결과로 대체될 수 있습니다.",
                    ]}
                    confirmLabel="분석 실행"
                    cancelLabel="취소"
                />

                {/* 이전 단계 재분석으로 인한 재분석 필요 모달 */}
                <ConfirmModal
                    isOpen={staleDataModalOpen}
                    onClose={() => setStaleDataModalOpen(false)}
                    onConfirm={() => {
                        setStaleDataModalOpen(false)
                        runTrackOnly()
                    }}
                    title="재분석 필요"
                    description={[
                        "이전 단계에서 재분석이 수행되었습니다.",
                        "현재 단계의 분석 결과가 최신 상태가 아닐 수 있습니다.",
                        "재분석을 실행하시겠습니까?",
                    ]}
                    confirmLabel="재분석"
                    cancelLabel="기존 결과 유지"
                />

                <div className="container">
                    <div className="flex gap-4">
                        <div className={isReferencePanelOpen ? "flex-[2] space-y-6" : "flex-1 space-y-6"}>
                            <div>
                                <h1 className="text-2xl font-bold mb-2">트랙 선택</h1>
                                <p className="text-muted-foreground">AI가 분석한 결과를 바탕으로 최적의 규제 샌드박스 트랙을 선택하세요</p>
                            </div>

                            <AIAnalysisCard summary={analysisResult.summary} confidence={analysisResult.confidence} />

                            <div className="space-y-4">
                                {analysisResult.recommendations.map((rec) => {
                                    const track = tracks.find((t) => t.id === rec.trackId)
                                    if (!track) return null

                                    const isSelected = effectiveSelectedTrackId === track.id
                                    const style = verdictStyles[rec.verdict] || verdictStyles["비추천"]

                                    return (
                                        <Card
                                            key={track.id}
                                            className={cn(
                                                "relative overflow-hidden transition-all cursor-pointer",
                                                isSelected && "ring-2 ring-primary"
                                            )}
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
                                                                            <span className="font-medium text-foreground">소요 기간:</span>{" "}
                                                                            {track.duration}
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
                                                <div className="space-y-2">
                                                    <ul className="space-y-2">
                                                        {rec.reasons.map((reason, index) => (
                                                            <li key={index} className="flex items-start gap-2 text-sm">
                                                                {getReasonIcon(reason.type)}
                                                                <div className="flex-1">
                                                                    <p className="text-base text-foreground">{reason.text}</p>
                                                                    {reason.source && (
                                                                        <p className="text-muted-foreground/70 mt-1">
                                                                            근거:{" "}
                                                                            {reason.sourceUrl ? (
                                                                                <a
                                                                                    href={reason.sourceUrl}
                                                                                    target="_blank"
                                                                                    rel="noopener noreferrer"
                                                                                    className="text-primary hover:underline inline-flex items-center gap-1"
                                                                                    onClick={(e) => e.stopPropagation()}
                                                                                >
                                                                                    {reason.source} <ExternalLink className="h-3 w-3" />
                                                                                </a>
                                                                            ) : (
                                                                                reason.source
                                                                            )}
                                                                            {reason.description ? ` - ${reason.description}` : ""}
                                                                        </p>
                                                                    )}
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
                                onReanalyze={isAheadOfCurrentStep || isAtCurrentStep ? handleReanalyze : undefined}
                                onNext={handleNext}
                                nextLabel="다음 단계"
                                isAnalyzed={!!analysisResult}
                                isLoading={isSaving || recommendMutation.isPending}
                            />
                        </div>

                        <div className={isReferencePanelOpen ? "flex-1" : ""}>
                            <div className="sticky top-24">
                                <ReferencePanel
                                    isOpen={isReferencePanelOpen}
                                    onToggle={() => setIsReferencePanelOpen(!isReferencePanelOpen)}
                                    cases={referenceCases.length > 0 ? referenceCases : undefined}
                                    regulations={referenceRegulations.length > 0 ? referenceRegulations : undefined}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </TooltipProvider>
    )
}
