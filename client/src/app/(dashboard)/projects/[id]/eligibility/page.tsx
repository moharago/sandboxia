"use client"

import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { ReferencePanel } from "@/components/features/draft/ReferencePanel"
import { WizardNavigation } from "@/components/features/wizard"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ConfirmModal } from "@/components/ui/confirm-modal"
import { NoResultsView } from "@/components/ui/no-results-view"
import { PageLoader } from "@/components/ui/page-loader"
import { useEligibilityMutation } from "@/hooks/mutations/use-eligibility-mutation"
import { useAgentNodesQuery } from "@/hooks/queries/use-agent-nodes-query"
import { useEligibilityQuery } from "@/hooks/queries/use-eligibility-query"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"
import { useAgentProgress } from "@/hooks/streaming/use-agent-progress"
import { agentsApi } from "@/lib/api/agents"
import { eligibilityApi } from "@/lib/api/eligibility"
import { projectsApi } from "@/lib/api/projects"
import { cn } from "@/lib/utils/cn"
import { getStepPagePath, PAGE_STEPS } from "@/lib/utils/step-utils"
import { useUIStore } from "@/stores/ui-store"
import { useWizardStore } from "@/stores/wizard-store"
import type { ApprovalCase, EligibilityResponse, EligibilityResult, JudgmentType, Regulation } from "@/types/api/eligibility"
import { useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, CheckCircle2, ExternalLink, Scale } from "lucide-react"
import { useRouter } from "next/navigation"
import { use, useEffect, useState } from "react"

type ReasonCategory = "law" | "regulation" | "case"

interface AnalysisReason {
    category: ReasonCategory
    title: string
    description: string
    source: string
    sourceUrl: string | null
}

const CATEGORY_CONFIG: Record<ReasonCategory, { label: string; badgeClass: string }> = {
    regulation: { label: "규제 기준", badgeClass: "bg-blue-100 text-blue-700 border-blue-300" },
    case: { label: "사례 기준", badgeClass: "bg-green-100 text-green-700 border-green-300" },
    law: { label: "법령 기준", badgeClass: "bg-purple-100 text-purple-700 border-purple-300" },
}

interface EligibilityPageProps {
    params: Promise<{ id: string }>
}

interface AIAnalysisData {
    recommendation: "direct" | "sandbox"
    confidence: number
    summary: string
    reasons: AnalysisReason[]
    directLaunchRisks: string[]
}

function mapJudgmentTypeToCategory(type: JudgmentType): ReasonCategory {
    switch (type) {
        case "규제 기준":
            return "regulation"
        case "사례 기준":
            return "case"
        case "법령 기준":
            return "law"
        default:
            return "regulation"
    }
}

function mapResponseToAnalysisData(response: EligibilityResponse | EligibilityResult): AIAnalysisData {
    const recommendation = response.eligibility_label === "not_required" ? "direct" : "sandbox"
    const confidence = Math.round(response.confidence_score * 100)
    const reasons: AnalysisReason[] = response.evidence_data.judgment_summary.map((item) => ({
        category: mapJudgmentTypeToCategory(item.type),
        title: item.title,
        description: item.summary,
        source: item.source,
        sourceUrl: item.source_url ?? null,
    }))
    const directLaunchRisks = response.direct_launch_risks.map((risk) => `${risk.title}: ${risk.description}`)
    return { recommendation, confidence, summary: response.result_summary, reasons, directLaunchRisks }
}

const defaultAnalysisData: AIAnalysisData = {
    recommendation: "sandbox",
    confidence: 0,
    summary: "AI 분석을 실행하여 규제 샌드박스 신청 필요 여부를 확인하세요.",
    reasons: [],
    directLaunchRisks: [],
}

type DecisionType = "direct" | "sandbox"
const PAGE_STEP = PAGE_STEPS.eligibility // 2

export default function EligibilityPage({ params }: EligibilityPageProps) {
    const { id } = use(params)
    const router = useRouter()
    const queryClient = useQueryClient()

    const { setMarketAnalysis, markStepComplete, setCurrentStep } = useWizardStore()
    const { devIsAnalyzed, devHasChanges, showGlobalAILoader, updateGlobalAILoader, hideGlobalAILoader } = useUIStore()

    // 프로젝트 정보 조회 (refetchOnMount: "always"로 자동 refetch)
    const { data: project, isPending: isLoadingProject } = useProjectQuery(id)
    const { data: existingResult, isPending: isLoadingExisting } = useEligibilityQuery(id)

    // 에이전트 노드 목록 조회
    const { data: eligibilityNodes } = useAgentNodesQuery("eligibility_evaluator")
    const { data: trackNodes } = useAgentNodesQuery("track_recommender")

    // 컴포넌트 마운트 시 전역 로더 숨기기
    useEffect(() => {
        hideGlobalAILoader()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // SSE 진행 상태 (전역 로더 자동 업데이트)
    const eligibilityProgress = useAgentProgress({
        projectId: id,
        useGlobalLoader: true,
        globalLoaderMessage: "서비스 규제 현황 분석 중...",
        globalLoaderNodes: eligibilityNodes?.nodes,
    })
    const trackProgress = useAgentProgress({
        projectId: id,
        useGlobalLoader: true,
        globalLoaderMessage: "최적의 트랙 추천 중...",
        globalLoaderNodes: trackNodes?.nodes,
    })

    // 현재 단계와 페이지 단계 비교
    const currentStep = project?.current_step ?? 1
    const isAheadOfCurrentStep = currentStep > PAGE_STEP
    const isAtCurrentStep = currentStep === PAGE_STEP
    const isBehindCurrentStep = currentStep < PAGE_STEP

    // 기존 결과 확인
    const hasExistingResult = existingResult?.evidence_data && Object.keys(existingResult.evidence_data).length > 0

    // 트랙 추천 결과 유무 (재분석 경고용)
    const [hasTrackResult, setHasTrackResult] = useState(false)
    useEffect(() => {
        if (id) eligibilityApi.hasTrackResult(id).then(setHasTrackResult)
    }, [id])

    // 모달 상태
    const [reanalyzeModalOpen, setReanalyzeModalOpen] = useState(false)
    const [staleDataModalOpen, setStaleDataModalOpen] = useState(false) // 이전 단계 재분석으로 인한 재분석 필요 모달
    const [errorModalOpen, setErrorModalOpen] = useState(false)
    const [errorMessage, setErrorMessage] = useState("")

    // current_step < PAGE_STEP이고 기존 데이터가 있는 경우 재분석 필요 모달 표시
    useEffect(() => {
        if (!isLoadingExisting && !isLoadingProject && isBehindCurrentStep && hasExistingResult) {
            setStaleDataModalOpen(true)
        }
    }, [isLoadingExisting, isLoadingProject, isBehindCurrentStep, hasExistingResult])

    // Mutation
    const eligibilityMutation = useEligibilityMutation({
        onSuccess: (data) => {
            const mappedData = mapResponseToAnalysisData(data)
            setAnalysisData(mappedData)
            setSelectedDecision(mappedData.recommendation)
            setIsAnalyzed(true)
            setApprovalCases(data.evidence_data.approval_cases ?? [])
            setRegulations(data.evidence_data.regulations ?? [])
            queryClient.invalidateQueries({ queryKey: ["projects"] })
        },
        onError: (error) => {
            eligibilityProgress.unsubscribe()
            hideGlobalAILoader()
            setErrorMessage(`분석 실패: ${error.message}`)
            setErrorModalOpen(true)
        },
    })

    // 분석 결과 상태
    const [analysisData, setAnalysisData] = useState<AIAnalysisData>(defaultAnalysisData)
    const [selectedDecision, setSelectedDecision] = useState<DecisionType>("sandbox")
    const [isAnalyzed, setIsAnalyzed] = useState(false)
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)
    const [isRunningTrackAgent, setIsRunningTrackAgent] = useState(false)
    const [approvalCases, setApprovalCases] = useState<ApprovalCase[]>()
    const [regulations, setRegulations] = useState<Regulation[]>()

    // 기존 결과 로드
    useEffect(() => {
        if (existingResult && hasExistingResult) {
            const mappedData = mapResponseToAnalysisData(existingResult)
            setAnalysisData(mappedData)
            setApprovalCases(existingResult.evidence_data.approval_cases ?? [])
            setRegulations(existingResult.evidence_data.regulations ?? [])
            if (existingResult.final_eligibility_label) {
                setSelectedDecision(existingResult.final_eligibility_label === "not_required" ? "direct" : "sandbox")
            } else {
                setSelectedDecision(mappedData.recommendation)
            }
            setIsAnalyzed(true)
        } else if (existingResult === null) {
            setAnalysisData(defaultAnalysisData)
            setSelectedDecision("sandbox")
            setIsAnalyzed(false)
        }
    }, [existingResult, hasExistingResult])

    const handleBack = () => {
        setCurrentStep(1)
        router.push(`/projects/${id}/service`)
    }

    // eligibility 분석만 실행 (재분석 - 페이지 이동 없음)
    const runEligibilityOnly = () => {
        setReanalyzeModalOpen(false)
        eligibilityProgress.subscribe()
        eligibilityMutation.mutate({ project_id: id }, {
            onSuccess: () => {
                hideGlobalAILoader() // 재분석 완료 시 로더 숨김
            },
        })
    }

    // 트랙 에이전트 실행 후 이동
    const runTrackAndNavigate = async () => {
        // sandbox인 경우 전역 로더 표시
        if (selectedDecision === "sandbox") {
            setIsRunningTrackAgent(true)
            showGlobalAILoader({
                message: "최적의 트랙 추천 중...",
                nodes: trackNodes?.nodes,
                progress: 0,
                completedNodes: [],
                currentNodeId: null,
            })
        }

        try {
            // 사용자 최종 선택 저장
            const finalLabel = selectedDecision === "direct" ? "not_required" : "required"

            if (selectedDecision === "direct") {
                // async-parallel: 독립적인 API 호출 병렬화
                await Promise.all([
                    eligibilityApi.updateFinalDecision(id, finalLabel),
                    projectsApi.updateStatus(id, 4, 2),
                ])
                // invalidateQueries는 await 불필요 (백그라운드 실행)
                queryClient.invalidateQueries({ queryKey: ["eligibility"] })
                queryClient.invalidateQueries({ queryKey: ["projects"] })
                markStepComplete(2)
                hideGlobalAILoader()
                router.push("/dashboard")
            } else {
                await eligibilityApi.updateFinalDecision(id, finalLabel)
                queryClient.invalidateQueries({ queryKey: ["eligibility"] })
                trackProgress.subscribe()
                await agentsApi.recommendTrack({ project_id: id })
                // invalidateQueries는 await 불필요 (백그라운드 실행)
                queryClient.invalidateQueries({ queryKey: ["track"] })
                queryClient.invalidateQueries({ queryKey: ["projects"] })
                markStepComplete(2)
                setCurrentStep(3)
                // 전역 로더는 다음 페이지에서 숨김
                router.push(`/projects/${id}/track`)
            }
        } catch (error) {
            console.error("트랙 추천/전환 실패:", error)
            const message = error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다."
            setErrorMessage(`처리 중 오류가 발생했습니다: ${message}`)
            setErrorModalOpen(true)
        } finally {
            trackProgress.unsubscribe()
            hideGlobalAILoader()
            setIsRunningTrackAgent(false)
        }
    }

    // 다음 페이지로 이동만 (분석 없이)
    const navigateToNext = () => {
        setMarketAnalysis({
            decision: selectedDecision,
            aiRecommendation: analysisData.recommendation,
        })

        if (selectedDecision === "direct") {
            router.push("/dashboard")
        } else {
            router.push(`/projects/${id}/track`)
        }
    }

    // 재분석 버튼 클릭
    const handleReanalyze = () => {
        setReanalyzeModalOpen(true)
    }

    // 다음 단계 버튼 클릭 (current_step > PAGE_STEP인 경우: 분석 없이 이동만)
    const handleNext = () => {
        if (!isAnalyzed) return

        if (isAheadOfCurrentStep) {
            // current_step > PAGE_STEP: 분석 없이 바로 이동
            navigateToNext()
        } else {
            // current_step == PAGE_STEP: 트랙 분석 후 이동
            runTrackAndNavigate()
        }
    }

    // 분석 + 다음 단계 (한 번에)
    const handleAnalyzeAndNext = () => {
        if (isAnalyzed) {
            handleNext()
            return
        }
        eligibilityProgress.subscribe()
        eligibilityMutation.mutate(
            { project_id: id },
            {
                onSuccess: async (data) => {
                    const mappedData = mapResponseToAnalysisData(data)

                    try {
                        // sandbox인 경우 전역 로더 메시지/노드 업데이트
                        if (mappedData.recommendation === "sandbox") {
                            setIsRunningTrackAgent(true)
                            showGlobalAILoader({
                                message: "최적의 트랙 추천 중...",
                                nodes: trackNodes?.nodes,
                                progress: 0,
                                completedNodes: [],
                                currentNodeId: null,
                            })
                        }

                        setMarketAnalysis({
                            decision: mappedData.recommendation,
                            aiRecommendation: mappedData.recommendation,
                        })

                        const finalLabel = mappedData.recommendation === "direct" ? "not_required" : "required"

                        if (mappedData.recommendation === "direct") {
                            // async-parallel: 독립적인 API 호출 병렬화
                            await Promise.all([
                                eligibilityApi.updateFinalDecision(id, finalLabel),
                                projectsApi.updateStatus(id, 4, 2),
                            ])
                            // invalidateQueries는 await 불필요 (백그라운드 실행)
                            queryClient.invalidateQueries({ queryKey: ["eligibility"] })
                            queryClient.invalidateQueries({ queryKey: ["projects"] })
                            markStepComplete(2)
                            hideGlobalAILoader()
                            router.push("/dashboard")
                        } else {
                            await eligibilityApi.updateFinalDecision(id, finalLabel)
                            queryClient.invalidateQueries({ queryKey: ["eligibility"] })
                            trackProgress.subscribe()
                            await agentsApi.recommendTrack({ project_id: id })
                            // invalidateQueries는 await 불필요 (백그라운드 실행)
                            queryClient.invalidateQueries({ queryKey: ["track"] })
                            queryClient.invalidateQueries({ queryKey: ["projects"] })
                            markStepComplete(2)
                            setCurrentStep(3)
                            // 전역 로더는 다음 페이지에서 숨김
                            router.push(`/projects/${id}/track`)
                        }
                    } catch (error) {
                        console.error("분석 후 처리 실패:", error)
                        const message = error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다."
                        setErrorMessage(`처리 중 오류가 발생했습니다: ${message}`)
                        setErrorModalOpen(true)
                    } finally {
                        trackProgress.unsubscribe()
                        hideGlobalAILoader()
                        setIsRunningTrackAgent(false)
                    }
                },
            }
        )
    }

    const isQueryLoading = isLoadingExisting || isLoadingProject

    // current_step < page_step이고 기존 데이터가 없는 경우: "분석 결과가 없습니다" 표시
    if (!isLoadingProject && !isLoadingExisting && project && isBehindCurrentStep && !hasExistingResult) {
        return <NoResultsView onNavigate={() => router.push(getStepPagePath(id, currentStep))} />
    }

    if (isQueryLoading) {
        return <PageLoader className="flex-1" />
    }

    return (
        <div className="py-6">
            {/* 재분석 확인 모달 */}
            <ConfirmModal
                isOpen={reanalyzeModalOpen}
                onClose={() => setReanalyzeModalOpen(false)}
                onConfirm={runEligibilityOnly}
                title="시장출시 진단 재분석"
                description={[
                    "이미 시장출시 진단이 완료된 상태입니다.",
                    "다시 분석하시겠습니까?",
                    hasTrackResult
                        ? "기존 분석 결과는 새로운 결과로 대체되며, 이후 단계(트랙 선택, 신청서 작성 등)도 재분석이 필요합니다."
                        : "기존 분석 결과는 새로운 결과로 대체될 수 있습니다.",
                ]}
                confirmLabel="분석 실행"
                cancelLabel="취소"
            />

            {/* 에러 모달 */}
            <ConfirmModal
                isOpen={errorModalOpen}
                onClose={() => setErrorModalOpen(false)}
                onConfirm={() => setErrorModalOpen(false)}
                title="오류 발생"
                description={errorMessage}
                confirmLabel="확인"
                cancelLabel="닫기"
            />

            {/* 이전 단계 재분석으로 인한 재분석 필요 모달 */}
            <ConfirmModal
                isOpen={staleDataModalOpen}
                onClose={() => setStaleDataModalOpen(false)}
                onConfirm={() => {
                    setStaleDataModalOpen(false)
                    runEligibilityOnly()
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
                            <h1 className="text-2xl font-bold mb-2">시장출시 진단</h1>
                            <p className="text-muted-foreground">AI가 서비스의 규제 현황을 분석하여 시장 출시 가능 여부를 판단합니다</p>
                        </div>

                        <AIAnalysisCard
                            summary={analysisData.summary}
                            confidence={analysisData.confidence}
                            recommendation={
                                !isAnalyzed
                                    ? "분석 대기 중"
                                    : analysisData.recommendation === "sandbox"
                                      ? "규제 샌드박스 필요"
                                      : "바로 시장 출시 가능"
                            }
                        />

                        {/* 판단 근거 */}
                        {isAnalyzed && analysisData.reasons.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>판단 근거</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="divide-y divide-border">
                                        {(analysisData.recommendation === "sandbox"
                                            ? (["regulation", "law", "case"] as ReasonCategory[])
                                            : (["regulation", "law"] as ReasonCategory[])
                                        )
                                            .map((category) => {
                                                const categoryReasons = analysisData.reasons.filter((r) => r.category === category)
                                                if (categoryReasons.length === 0) return null
                                                const config = CATEGORY_CONFIG[category]
                                                return (
                                                    <div key={category} className="py-4 first:pt-0 last:pb-0">
                                                        <div className="flex items-start gap-3">
                                                            <Badge
                                                                variant="outline"
                                                                className={cn("shrink-0 mt-0.5 text-xs font-medium", config.badgeClass)}
                                                            >
                                                                {config.label}
                                                            </Badge>
                                                            <div className="flex-1 space-y-4">
                                                                {categoryReasons.map((reason, idx) => (
                                                                    <div key={idx}>
                                                                        <h4 className="text-[17px] font-medium">{reason.title}</h4>
                                                                        <p className="text-sm text-foreground mt-1">{reason.description}</p>
                                                                        <p className="text-[13px] text-foreground/70 mt-2">
                                                                            근거:{" "}
                                                                            {reason.sourceUrl ? (
                                                                                <a
                                                                                    href={reason.sourceUrl}
                                                                                    target="_blank"
                                                                                    rel="noopener noreferrer"
                                                                                    className="text-primary hover:underline inline-flex items-center gap-1"
                                                                                >
                                                                                    {reason.source} <ExternalLink className="h-3 w-3" />
                                                                                </a>
                                                                            ) : (
                                                                                reason.source
                                                                            )}
                                                                        </p>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </div>
                                                )
                                            })
                                            .filter(Boolean)}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* 참고 사례 */}
                        {isAnalyzed &&
                            analysisData.recommendation === "direct" &&
                            analysisData.reasons.filter((r) => r.category === "case").length > 0 && (
                                <Card>
                                    <CardHeader>
                                        <CardTitle>참고 사례</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="divide-y divide-border">
                                            {analysisData.reasons
                                                .filter((r) => r.category === "case")
                                                .map((reason, idx) => (
                                                    <div key={idx} className="py-4 first:pt-0 last:pb-0">
                                                        <div className="flex items-start gap-3">
                                                            <Badge
                                                                variant="outline"
                                                                className={cn("shrink-0 mt-0.5 text-xs font-medium", CATEGORY_CONFIG.case.badgeClass)}
                                                            >
                                                                {CATEGORY_CONFIG.case.label}
                                                            </Badge>
                                                            <div className="flex-1">
                                                                <h4 className="text-[17px] font-medium">{reason.title}</h4>
                                                                <p className="text-sm text-foreground mt-1">{reason.description}</p>
                                                                <p className="text-[13px] text-foreground/70 mt-2">
                                                                    근거:{" "}
                                                                    {reason.sourceUrl ? (
                                                                        <a
                                                                            href={reason.sourceUrl}
                                                                            target="_blank"
                                                                            rel="noopener noreferrer"
                                                                            className="text-primary hover:underline inline-flex items-center gap-1"
                                                                        >
                                                                            {reason.source} <ExternalLink className="h-3 w-3" />
                                                                        </a>
                                                                    ) : (
                                                                        reason.source
                                                                    )}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            )}

                        {/* 바로 출시 시 리스크 */}
                        {isAnalyzed && analysisData.recommendation === "sandbox" && analysisData.directLaunchRisks.length > 0 && (
                            <Card className="border-amber-200">
                                <CardHeader>
                                    <div className="flex items-center gap-2">
                                        <AlertTriangle className="h-5 w-5 text-amber-500" />
                                        <CardTitle className="text-amber-700">바로 출시 시 예상 리스크</CardTitle>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <ul className="space-y-2">
                                        {analysisData.directLaunchRisks.map((risk, index) => (
                                            <li key={index} className="flex items-start gap-2 text-sm">
                                                <span className="h-1.5 w-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                                                {risk}
                                            </li>
                                        ))}
                                    </ul>
                                </CardContent>
                            </Card>
                        )}

                        {/* 최종 결정 */}
                        {isAnalyzed && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>최종 결정</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <button
                                            type="button"
                                            onClick={() => setSelectedDecision("direct")}
                                            className={cn(
                                                "p-4 rounded-lg border-2 text-left transition-all",
                                                selectedDecision === "direct"
                                                    ? "border-primary bg-primary/5"
                                                    : "border-border hover:border-primary/50"
                                            )}
                                        >
                                            <div className="flex items-center gap-3">
                                                <CheckCircle2
                                                    className={cn(
                                                        "h-6 w-6",
                                                        selectedDecision === "direct" ? "text-primary" : "text-muted-foreground"
                                                    )}
                                                />
                                                <div>
                                                    <h4 className="font-medium">바로 시장 출시</h4>
                                                    <p className="text-sm text-muted-foreground">현행 규제 내에서 서비스 출시가 가능합니다</p>
                                                </div>
                                            </div>
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() => setSelectedDecision("sandbox")}
                                            className={cn(
                                                "p-4 rounded-lg border-2 text-left transition-all",
                                                selectedDecision === "sandbox"
                                                    ? "border-primary bg-primary/5"
                                                    : "border-border hover:border-primary/50"
                                            )}
                                        >
                                            <div className="flex items-center gap-3">
                                                <Scale
                                                    className={cn(
                                                        "h-6 w-6",
                                                        selectedDecision === "sandbox" ? "text-primary" : "text-muted-foreground"
                                                    )}
                                                />
                                                <div>
                                                    <h4 className="font-medium">규제 샌드박스 신청</h4>
                                                    <p className="text-sm text-muted-foreground">규제 특례를 통한 실증이 필요합니다</p>
                                                </div>
                                            </div>
                                        </button>
                                    </div>

                                    {selectedDecision !== analysisData.recommendation && (
                                        <div className="text-sm flex gap-2 items-center px-2">
                                            <AlertTriangle className="h-4 w-4 text-amber-500" />
                                            <span className="text-amber-700">AI 추천과 다른 선택입니다.</span>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        <WizardNavigation
                            onBack={handleBack}
                            onAnalyze={isAtCurrentStep && !isAnalyzed ? handleAnalyzeAndNext : undefined}
                            onReanalyze={isAheadOfCurrentStep || (isAtCurrentStep && isAnalyzed) ? handleReanalyze : undefined}
                            onNext={isAnalyzed ? handleNext : undefined}
                            analyzeLabel="AI 분석 및 다음 단계"
                            nextLabel={selectedDecision === "direct" ? "완료" : "다음 단계"}
                            isAnalyzed={isAheadOfCurrentStep || isAnalyzed || devIsAnalyzed}
                            hasChanges={devHasChanges}
                            isLoading={eligibilityMutation.isPending || isQueryLoading || isRunningTrackAgent}
                        />
                    </div>

                    <div className={isReferencePanelOpen ? "flex-1 min-w-0" : ""}>
                        <div className="sticky top-16">
                            <ReferencePanel
                                isOpen={isReferencePanelOpen}
                                onToggle={() => setIsReferencePanelOpen(!isReferencePanelOpen)}
                                approvalCases={approvalCases}
                                regulations={regulations}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
