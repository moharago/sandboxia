"use client"

import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { ReferencePanel } from "@/components/features/draft/ReferencePanel"
import { WizardNavigation } from "@/components/features/wizard"
import { AILoader } from "@/components/ui/ai-loader"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import { useUIStore } from "@/stores/ui-store"
import { useWizardStore } from "@/stores/wizard-store"
import type { ApprovalCase, EligibilityResponse, EligibilityResult, JudgmentType, Regulation } from "@/types/api/eligibility"
import { useQueryClient } from "@tanstack/react-query"
import { AlertCircle, AlertTriangle, CheckCircle2, ExternalLink, Scale } from "lucide-react"
import { useRouter } from "next/navigation"
import { use, useEffect, useRef, useState } from "react"

type ReasonCategory = "law" | "regulation" | "case"

interface AnalysisReason {
    category: ReasonCategory
    title: string
    description: string
    source: string
    sourceUrl: string | null
}

const CATEGORY_CONFIG: Record<ReasonCategory, { label: string; badgeClass: string }> = {
    regulation: {
        label: "규제 기준",
        badgeClass: "bg-blue-100 text-blue-700 border-blue-300",
    },
    case: {
        label: "사례 기준",
        badgeClass: "bg-green-100 text-green-700 border-green-300",
    },
    law: {
        label: "법령 기준",
        badgeClass: "bg-purple-100 text-purple-700 border-purple-300",
    },
}

interface MarketPageProps {
    params: Promise<{ id: string }>
}

// API 응답을 UI 데이터로 변환
interface AIAnalysisData {
    recommendation: "direct" | "sandbox"
    confidence: number
    summary: string
    reasons: AnalysisReason[]
    directLaunchRisks: string[]
}

// JudgmentType을 ReasonCategory로 변환
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

// API 응답 또는 DB 레코드를 UI 데이터로 변환
function mapResponseToAnalysisData(response: EligibilityResponse | EligibilityResult): AIAnalysisData {
    // eligibility_label → recommendation 변환
    const recommendation = response.eligibility_label === "not_required" ? "direct" : "sandbox"

    // confidence_score (0-1) → confidence (0-100) 변환
    const confidence = Math.round(response.confidence_score * 100)

    // judgment_summary → reasons 변환
    const reasons: AnalysisReason[] = response.evidence_data.judgment_summary.map((item) => ({
        category: mapJudgmentTypeToCategory(item.type),
        title: item.title,
        description: item.summary,
        source: item.source,
        sourceUrl: item.source_url ?? null,
    }))

    // direct_launch_risks → directLaunchRisks 변환 (description만 추출)
    const directLaunchRisks = response.direct_launch_risks.map((risk) => `${risk.title}: ${risk.description}`)

    return {
        recommendation,
        confidence,
        summary: response.result_summary,
        reasons,
        directLaunchRisks,
    }
}

// 분석 전 기본 UI 데이터
const defaultAnalysisData: AIAnalysisData = {
    recommendation: "sandbox",
    confidence: 0,
    summary: "AI 분석을 실행하여 규제 샌드박스 신청 필요 여부를 확인하세요.",
    reasons: [],
    directLaunchRisks: [],
}

type DecisionType = "direct" | "sandbox"

export default function EligibilityPage({ params }: MarketPageProps) {
    const { id } = use(params)
    const router = useRouter()
    const queryClient = useQueryClient()

    const { setMarketAnalysis, markStepComplete, setCurrentStep } = useWizardStore()
    const { devIsAnalyzed, devHasChanges } = useUIStore()

    // 프로젝트 정보 조회 (current_step 확인용)
    const { data: project, isLoading: isLoadingProject } = useProjectQuery(id)

    // 기존 eligibility 결과 조회
    const { data: existingResult, isLoading: isLoadingExisting } = useEligibilityQuery(id)

    // 에이전트 노드 목록 조회 (스트리밍 체크리스트용)
    const { data: eligibilityNodes } = useAgentNodesQuery("eligibility_evaluator")
    const { data: trackNodes } = useAgentNodesQuery("track_recommender")

    // SSE 진행 상태 구독
    const eligibilityProgress = useAgentProgress({
        projectId: id,
        onComplete: () => {
            // 완료 시 캐시 갱신
            queryClient.invalidateQueries({ queryKey: ["eligibility"] })
        },
    })
    const trackProgress = useAgentProgress({
        projectId: id,
        onComplete: () => {
            queryClient.invalidateQueries({ queryKey: ["track"] })
        },
    })

    // 트랙 추천 결과 유무 (재분석 경고용)
    const [hasTrackResult, setHasTrackResult] = useState(false)
    useEffect(() => {
        if (id) {
            eligibilityApi.hasTrackResult(id).then(setHasTrackResult)
        }
    }, [id])

    // 기존 결과가 있는지 확인 (evidence_data가 있고 비어있지 않은 경우)
    const hasExistingResult = existingResult?.evidence_data && Object.keys(existingResult.evidence_data).length > 0

    // Step 1 완료 여부 확인 (current_step >= 2이면 Step 1 완료)
    const isStep1Completed = project && project.current_step >= 2

    // Step 1 미완료 시 alert 후 리다이렉트 (Strict Mode 중복 방지)
    const hasRedirected = useRef(false)
    // useEffect(() => {
    //     if (!isLoadingProject && project && !isStep1Completed && !hasRedirected.current) {
    //         hasRedirected.current = true
    //         alert("서비스 분석을 먼저 완료해주세요.")
    //         router.push(`/projects/${id}/service`)
    //     }
    // }, [isLoadingProject, project, isStep1Completed, router, id])

    // API mutation hook
    const eligibilityMutation = useEligibilityMutation({
        onSuccess: (data) => {
            const mappedData = mapResponseToAnalysisData(data)
            setAnalysisData(mappedData)
            setSelectedDecision(mappedData.recommendation)
            setIsAnalyzed(true)
            setApprovalCases(data.evidence_data.approval_cases ?? [])
            setRegulations(data.evidence_data.regulations ?? [])
        },
        onError: (error) => {
            alert(`분석 실패: ${error.message}`)
        },
    })

    // 분석 결과 상태
    const [analysisData, setAnalysisData] = useState<AIAnalysisData>(defaultAnalysisData)
    const [selectedDecision, setSelectedDecision] = useState<DecisionType>("sandbox")
    const [isAnalyzed, setIsAnalyzed] = useState(false)
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)
    const [isRunningTrackAgent, setIsRunningTrackAgent] = useState(false)

    // 오른쪽 패널용 데이터
    const [approvalCases, setApprovalCases] = useState<ApprovalCase[]>()
    const [regulations, setRegulations] = useState<Regulation[]>()

    // 기존 결과가 로드되면 화면에 표시
    useEffect(() => {
        if (existingResult && hasExistingResult) {
            const mappedData = mapResponseToAnalysisData(existingResult)
            setAnalysisData(mappedData)
            setApprovalCases(existingResult.evidence_data.approval_cases ?? [])
            setRegulations(existingResult.evidence_data.regulations ?? [])

            // 사용자가 이미 선택한 값이 있으면 그걸 사용, 없으면 AI 추천값 사용
            if (existingResult.final_eligibility_label) {
                // final_eligibility_label: "not_required" → "direct", "required" → "sandbox"
                const userChoice = existingResult.final_eligibility_label === "not_required" ? "direct" : "sandbox"
                setSelectedDecision(userChoice)
            } else {
                setSelectedDecision(mappedData.recommendation)
            }

            setIsAnalyzed(true)
        } else if (existingResult === null) {
            // 결과가 없으면 초기 상태로
            setAnalysisData(defaultAnalysisData)
            setSelectedDecision("sandbox")
            setIsAnalyzed(false)
        }
    }, [existingResult, hasExistingResult])

    const handleBack = () => {
        setCurrentStep(1)
        router.push(`/projects/${id}/service`)
    }

    // 재분석 확인 (기존 결과가 있으면 confirm, 없으면 바로 true)
    const confirmReanalysis = (): boolean => {
        if (!hasExistingResult) return true
        const message = hasTrackResult
            ? "이미 대상성 분석이 완료된 프로젝트입니다.\n다시 분석하시겠습니까?\n\n기존 분석 결과는 새로운 결과로 대체될 수 있으며,\n트랙 추천 등 이후 단계도 재분석이 필요합니다."
            : "이미 대상성 분석이 완료된 프로젝트입니다.\n다시 분석하시겠습니까?\n\n기존 분석 결과는 새로운 결과로 대체될 수 있습니다."
        return window.confirm(message)
    }

    // AI 분석 실행 (분석만, 다음 단계로 안 감)
    const handleAnalyze = () => {
        if (!confirmReanalysis()) return
        eligibilityProgress.subscribe() // SSE 구독 시작
        runAnalysis(false)
    }

    // 다음 단계로 이동 (분석 완료 후)
    const handleNext = async () => {
        if (!isAnalyzed) return

        setMarketAnalysis({
            decision: selectedDecision,
            aiRecommendation: analysisData.recommendation,
        })

        // 사용자 최종 선택 저장 (direct → not_required, sandbox → required)
        const finalLabel = selectedDecision === "direct" ? "not_required" : "required"
        await eligibilityApi.updateFinalDecision(id, finalLabel)
        await queryClient.invalidateQueries({ queryKey: ["eligibility"] }) // eligibility 캐시 무효화

        if (selectedDecision === "direct") {
            // 바로출시 선택 → current_step=5, status=4 (completed)
            await projectsApi.updateStatus(id, 4, 5)
            await queryClient.invalidateQueries({ queryKey: ["projects"] })
            markStepComplete(2)
            router.push("/dashboard")
        } else {
            // 샌드박스 신청 선택 → 트랙 추천 에이전트 실행 후 이동
            await queryClient.invalidateQueries({ queryKey: ["projects"] })
            try {
                setIsRunningTrackAgent(true)
                trackProgress.subscribe() // SSE 구독 시작
                await agentsApi.recommendTrack({ project_id: id })
            } catch (error) {
                console.error("트랙 추천 실패:", error)
                alert("트랙 추천 중 오류가 발생했습니다. 다시 시도해주세요.")
                setIsRunningTrackAgent(false)
                trackProgress.reset()
                return
            }
            setIsRunningTrackAgent(false)
            markStepComplete(2)
            setCurrentStep(3)
            router.push(`/projects/${id}/track`)
        }
    }

    // AI 분석 실행 (재분석 확인 포함)
    const runAnalysis = (goNextAfter: boolean) => {
        eligibilityMutation.mutate(
            { project_id: id },
            {
                onSuccess: async (data) => {
                    const mappedData = mapResponseToAnalysisData(data)
                    setAnalysisData(mappedData)
                    setSelectedDecision(mappedData.recommendation)
                    setIsAnalyzed(true)

                    // 서버에서 current_step이 변경될 수 있으므로 프로젝트 캐시 갱신
                    await queryClient.invalidateQueries({ queryKey: ["projects"] })

                    if (goNextAfter) {
                        // 바로 다음 단계로 이동
                        setMarketAnalysis({
                            decision: mappedData.recommendation,
                            aiRecommendation: mappedData.recommendation,
                        })

                        // 사용자 최종 선택 저장 (AI 추천 그대로 수락)
                        const finalLabel = mappedData.recommendation === "direct" ? "not_required" : "required"
                        await eligibilityApi.updateFinalDecision(id, finalLabel)
                        await queryClient.invalidateQueries({ queryKey: ["eligibility"] })

                        if (mappedData.recommendation === "direct") {
                            // 바로출시 → status=4, current_step=5 (completed)
                            await projectsApi.updateStatus(id, 4, 5)
                            await queryClient.invalidateQueries({ queryKey: ["projects"] })
                            markStepComplete(2)
                            router.push("/dashboard")
                        } else {
                            // 샌드박스 신청 → 트랙 추천 에이전트 실행 후 이동
                            await queryClient.invalidateQueries({ queryKey: ["projects"] })
                            try {
                                setIsRunningTrackAgent(true)
                                trackProgress.subscribe() // SSE 구독 시작
                                await agentsApi.recommendTrack({ project_id: id })
                            } catch (error) {
                                console.error("트랙 추천 실패:", error)
                                alert("트랙 추천 중 오류가 발생했습니다. 다시 시도해주세요.")
                                setIsRunningTrackAgent(false)
                                trackProgress.reset()
                                return
                            }
                            setIsRunningTrackAgent(false)
                            markStepComplete(2)
                            setCurrentStep(3)
                            router.push(`/projects/${id}/track`)
                        }
                    }
                },
            }
        )
    }

    // 분석 + 다음 단계 (한 번에)
    const handleAnalyzeAndNext = () => {
        // 이미 분석된 경우 바로 다음 단계로
        if (isAnalyzed) {
            handleNext()
            return
        }

        // 기존 결과가 있으면 재분석 확인
        if (!confirmReanalysis()) {
            // 취소하면 기존 결과로 다음 단계 진행
            handleNext()
            return
        }

        // SSE 구독 시작 후 분석 실행
        eligibilityProgress.subscribe()
        runAnalysis(true)
    }

    const isQueryLoading = isLoadingExisting || isLoadingProject

    // Step 1 완료 전이면 안내 화면 표시 (project가 있을 때만)
    if (!isLoadingProject && project && !isStep1Completed) {
        return (
            <div className="py-6">
                <div className="container">
                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="text-center space-y-4">
                            <AlertCircle className="h-12 w-12 mx-auto text-amber-500" />
                            <h2 className="text-lg font-semibold">서비스 분석이 필요합니다</h2>
                            <p className="text-muted-foreground">이전 단계(서비스 분석)를 먼저 완료해주세요.</p>
                            <button
                                type="button"
                                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
                                onClick={() => router.push(`/projects/${id}/service`)}
                            >
                                이전 단계로 돌아가기
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // 데이터 로딩 중
    if (isQueryLoading) {
        return <PageLoader className="flex-1" />
    }

    return (
        <div className="py-6">
            {eligibilityMutation.isPending && (
                <AILoader
                    message="서비스 규제 현황 분석 중..."
                    nodes={eligibilityNodes?.nodes}
                    completedNodes={eligibilityProgress.completedNodes}
                    currentNodeId={eligibilityProgress.currentNodeId}
                    progress={eligibilityProgress.progress}
                />
            )}
            {isRunningTrackAgent && (
                <AILoader
                    message="최적의 트랙 추천 중..."
                    nodes={trackNodes?.nodes}
                    completedNodes={trackProgress.completedNodes}
                    currentNodeId={trackProgress.currentNodeId}
                    progress={trackProgress.progress}
                />
            )}
            <div className="container">
                <div className="flex gap-4">
                    {/* 왼쪽: 메인 콘텐츠 */}
                    <div className={isReferencePanelOpen ? "flex-[2] space-y-6" : "flex-1 space-y-6"}>
                        <div>
                            <h1 className="text-2xl font-bold mb-2">시장출시 진단</h1>
                            <p className="text-muted-foreground">AI가 서비스의 규제 현황을 분석하여 시장 출시 가능 여부를 판단합니다</p>
                        </div>

                        {/* AI 분석 요약 */}
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
                                        {/* sandbox(required): 규제+법령+사례 모두 표시 / direct(not_required): 규제+법령만 */}
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
                                                                        <h4 className="font-medium">{reason.title}</h4>
                                                                        <p className="text-sm text-foreground mt-1">{reason.description}</p>
                                                                        <p className="text-sm text-foreground/70 mt-2">
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

                        {/* 참고 사례 - not_required일 때만 별도 카드로 표시 */}
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
                                                                <h4 className="font-medium">{reason.title}</h4>
                                                                <p className="text-sm text-foreground mt-1">{reason.description}</p>
                                                                <p className="text-sm text-foreground/70 mt-2">
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

                        {/* 컨설턴트 최종 결정 */}
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
                                            <span className="text-amber-700">AI 추천과 다른 선택입니다. 선택에 대한 근거를 확인해주세요.</span>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        <WizardNavigation
                            onBack={handleBack}
                            onAnalyze={handleAnalyzeAndNext}
                            onReanalyze={handleAnalyze}
                            onNext={handleNext}
                            analyzeLabel="AI 분석 및 다음 단계"
                            nextLabel={selectedDecision === "direct" ? "완료" : "다음 단계"}
                            isAnalyzed={isAnalyzed || devIsAnalyzed}
                            hasChanges={devHasChanges}
                            isLoading={eligibilityMutation.isPending || isQueryLoading || isRunningTrackAgent}
                        />
                    </div>

                    {/* 오른쪽: 참고 패널 */}
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
