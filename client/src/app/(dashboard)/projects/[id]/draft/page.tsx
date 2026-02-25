"use client"

import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { DownloadModal } from "@/components/features/draft/DownloadModal"
import { FormSectionList } from "@/components/features/draft/FormSectionList"
import { ReferencePanel } from "@/components/features/draft/ReferencePanel"
import { WizardNavigation } from "@/components/features/wizard"
import { AILoader } from "@/components/ui/ai-loader"
import { Button } from "@/components/ui/button"
import { ConfirmModal } from "@/components/ui/confirm-modal"
import { NoResultsView } from "@/components/ui/no-results-view"
import { PageLoader } from "@/components/ui/page-loader"
import { useDraftGenerateMutation } from "@/hooks/mutations/use-draft-mutation"
import { useAgentNodesQuery } from "@/hooks/queries/use-agent-nodes-query"
import { draftKeys, useDraftQuery } from "@/hooks/queries/use-draft-query"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"
import { useAgentProgress } from "@/hooks/streaming/use-agent-progress"
import { projectsApi } from "@/lib/api/projects"
import { getStepPagePath, PAGE_STEPS } from "@/lib/utils/step-utils"
import { useWizardStore, type FormType } from "@/stores/wizard-store"
import type { ApprovalCase, Regulation } from "@/types/api/eligibility"
import { TRACK_TO_FORM_ID, type Track } from "@/types/data/project"
import { useQueryClient } from "@tanstack/react-query"
import { AlertCircle, Download, Sparkles } from "lucide-react"
import { useRouter } from "next/navigation"
import { use, useEffect, useState } from "react"

/** Track 타입 가드: TRACK_TO_FORM_ID에 존재하는 유효한 Track인지 확인 */
const isTrack = (value: string | null | undefined): value is Track => value != null && Object.prototype.hasOwnProperty.call(TRACK_TO_FORM_ID, value)

const PAGE_STEP = PAGE_STEPS.draft // 4

interface DraftPageProps {
    params: Promise<{ id: string }>
}

export default function DraftPage({ params }: DraftPageProps) {
    const { id } = use(params)
    const router = useRouter()
    const queryClient = useQueryClient()

    const { markStepComplete, setCurrentStep } = useWizardStore()
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false)

    // 모달 상태
    const [regenerateModalOpen, setRegenerateModalOpen] = useState(false)
    const [completeModalOpen, setCompleteModalOpen] = useState(false)
    const [staleDataModalOpen, setStaleDataModalOpen] = useState(false) // 이전 단계 재분석으로 인한 재분석 필요 모달
    const [errorModalOpen, setErrorModalOpen] = useState(false)
    const [errorMessage, setErrorMessage] = useState("")

    // RAG 결과 state (mutation 성공 시 바로 표시용)
    const [ragSimilarCases, setRagSimilarCases] = useState<ApprovalCase[]>([])
    const [ragRegulations, setRagRegulations] = useState<Regulation[]>([])

    // 프로젝트에서 track 정보 조회
    const { data: project, isLoading: isLoadingProject, refetch: refetchProject } = useProjectQuery(id)

    // 현재 단계와 페이지 단계 비교
    const currentStep = project?.current_step ?? 1
    const isAtOrAheadOfCurrentStep = currentStep >= PAGE_STEP // 분석 완료된 상태
    const isBehindCurrentStep = currentStep < PAGE_STEP // 이전 단계가 완료되지 않은 상태

    // Supabase에서 초안 데이터 조회
    const { data: draftData, isLoading: isLoadingDraft, refetch: refetchDraft } = useDraftQuery(id)

    // StepNav로 페이지 진입 시 데이터 refetch
    useEffect(() => {
        refetchProject()
        refetchDraft()
    }, [refetchProject, refetchDraft])

    // 기존 결과 확인 (빈 객체 {}는 false로 처리)
    const hasDraftData = !!draftData?.form_values && typeof draftData.form_values === "object" && Object.keys(draftData.form_values).length > 0

    // current_step < PAGE_STEP이고 기존 데이터가 있는 경우 재분석 필요 모달 표시
    useEffect(() => {
        if (!isLoadingDraft && !isLoadingProject && isBehindCurrentStep && hasDraftData) {
            setStaleDataModalOpen(true)
        }
    }, [isLoadingDraft, isLoadingProject, isBehindCurrentStep, hasDraftData])

    // 에이전트 노드 목록 조회 (스트리밍 체크리스트용)
    const { data: draftNodes } = useAgentNodesQuery("application_drafter")

    // SSE 진행 상태 구독
    const draftProgress = useAgentProgress({
        projectId: id,
        onComplete: () => {
            queryClient.invalidateQueries({ queryKey: draftKeys.byProject(id) })
        },
    })

    // AI 초안 생성 mutation
    const draftMutation = useDraftGenerateMutation()

    // track → formType 변환 (런타임 타입 검증)
    const formType: FormType | null = isTrack(project?.track) ? TRACK_TO_FORM_ID[project.track] : null

    // application_draft.form_values를 그대로 initialValues로 사용
    const initialValues = draftData?.form_values

    // AI 초안 생성 실행
    const runDraftGeneration = async () => {
        setRegenerateModalOpen(false)
        // 재생성 시 current_step을 현재 페이지 단계(4)로 업데이트
        await projectsApi.updateStatus(id, project?.status ?? 3, PAGE_STEP)
        await queryClient.invalidateQueries({ queryKey: ["projects"] })
        draftProgress.subscribe() // SSE 구독 시작
        try {
            const result = await draftMutation.mutateAsync({ project_id: id })
            // RAG 결과를 state에 저장 (바로 표시)
            setRagSimilarCases(result.similar_cases ?? [])
            setRagRegulations(result.domain_laws ?? [])
            // 성공 시 draft query invalidate하여 새 데이터 로드
            queryClient.invalidateQueries({ queryKey: draftKeys.byProject(id) })
            queryClient.invalidateQueries({ queryKey: ["projects"] })
        } catch (error) {
            const message = error instanceof Error ? error.message : "알 수 없는 오류"
            setErrorMessage(`AI 초안 생성에 실패했습니다: ${message}`)
            setErrorModalOpen(true)
        }
    }

    // AI 재생성 버튼 클릭 (확인 모달 표시)
    const handleRegenerate = () => {
        setRegenerateModalOpen(true)
    }

    // 작성 완료 버튼 클릭 (확인 모달 표시)
    const handleCompleteClick = () => {
        setCompleteModalOpen(true)
    }

    // 작성 완료 확정
    const confirmComplete = () => {
        setCompleteModalOpen(false)
        markStepComplete(4)
        router.push("/dashboard")
    }

    // RAG 결과: state 우선, 없으면 DB에서 읽기
    const similarCases = ragSimilarCases.length > 0 ? ragSimilarCases : ((draftData?.similar_cases as ApprovalCase[]) ?? [])
    const regulations = ragRegulations.length > 0 ? ragRegulations : ((draftData?.domain_laws as Regulation[]) ?? [])

    const handleBack = () => {
        setCurrentStep(3)
        router.push(`/projects/${id}/track`)
    }

    // 데이터 로딩 중
    if (isLoadingProject || isLoadingDraft) {
        return <PageLoader className="flex-1" />
    }

    // AI 초안 생성 중
    if (draftMutation.isPending) {
        return (
            <AILoader
                message="신청서 초안 생성 중..."
                nodes={draftNodes?.nodes}
                completedNodes={draftProgress.completedNodes}
                currentNodeId={draftProgress.currentNodeId}
                progress={draftProgress.progress}
            />
        )
    }

    // current_step < PAGE_STEP이고 기존 데이터가 없는 경우: "분석 결과가 없습니다" 표시
    if ((isBehindCurrentStep && !hasDraftData) || !project?.track) {
        return <NoResultsView onNavigate={() => router.push(getStepPagePath(id, currentStep))} />
    }

    // 트랙 불일치 감지: 저장된 초안의 track과 현재 프로젝트의 track이 다른 경우
    const isTrackMismatch = hasDraftData && draftData?.track && draftData.track !== project.track

    return (
        <div className="py-6">
            <div className="container">
                <div className="flex gap-4">
                    {/* 왼쪽: 폼 영역 */}
                    <div className={isReferencePanelOpen ? "flex-[2] space-y-6" : "flex-1 space-y-6"}>
                        <div>
                            <h1 className="text-2xl font-bold mb-2">신청서 작성</h1>
                            <p className="text-muted-foreground">
                                {hasDraftData ? "AI가 생성한 초안을 검토하고 수정하세요" : "AI 초안 생성 버튼을 눌러 신청서 초안을 생성하세요"}
                            </p>
                        </div>

                        {isTrackMismatch ? (
                            <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
                                <div className="flex items-start gap-3">
                                    <AlertCircle className="h-6 w-6 text-amber-500 shrink-0 mt-0.5" />
                                    <div className="flex-1">
                                        <h3 className="text-lg font-semibold text-amber-800 mb-1">트랙이 변경되어 초안을 다시 생성해야 합니다</h3>
                                        <p className="text-amber-700 text-sm mb-4">
                                            이전에 생성된 초안은 다른 트랙 기준으로 작성되었습니다. 변경된 트랙에 맞는 신청서를 작성하려면 초안을 다시
                                            생성해주세요.
                                        </p>
                                        <Button
                                            onClick={runDraftGeneration}
                                            variant="outline"
                                            className="gap-2 border-amber-400 text-amber-700 hover:bg-amber-100"
                                            disabled={draftMutation.isPending}
                                        >
                                            <Sparkles className="h-4 w-4" />
                                            AI 초안 다시 생성
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        ) : hasDraftData ? (
                            <AIAnalysisCard
                                title="AI 초안 생성 완료"
                                summary="AI가 생성한 초안이 아래 폼에 자동으로 채워졌습니다. 내용을 검토하고 필요에 따라 수정하세요."
                            />
                        ) : (
                            <div className="bg-muted/50 border border-dashed rounded-lg p-8 text-center">
                                <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                                <h3 className="text-lg font-medium mb-2">AI 초안을 생성해주세요</h3>
                                <p className="text-muted-foreground mb-4">
                                    버튼을 클릭하면 AI가 서비스 정보를 기반으로 신청서 초안을 자동 생성합니다.
                                </p>
                                <Button onClick={runDraftGeneration} className="gap-2" disabled={draftMutation.isPending}>
                                    <Sparkles className="h-4 w-4" />
                                    AI 초안 생성
                                </Button>
                            </div>
                        )}

                        {/* 동적 폼 필드 카드 */}
                        {formType ? (
                            <FormSectionList formType={formType} initialValues={isTrackMismatch ? undefined : initialValues} projectId={id} />
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">폼 타입을 확인할 수 없습니다.</div>
                        )}

                        <WizardNavigation
                            onBack={handleBack}
                            onNext={hasDraftData && !isTrackMismatch ? handleCompleteClick : undefined}
                            onAnalyze={!hasDraftData || isTrackMismatch ? runDraftGeneration : undefined}
                            nextLabel="작성 완료"
                            analyzeLabel="AI 초안 생성"
                            isAnalyzed={hasDraftData && !isTrackMismatch}
                            isLoading={draftMutation.isPending}
                            extraButtons={
                                <>
                                    {hasDraftData && !isTrackMismatch && (
                                        <Button variant="outline" onClick={handleRegenerate} className="gap-2">
                                            <Sparkles className="h-4 w-4" />
                                            AI 재생성
                                        </Button>
                                    )}
                                    <Button
                                        variant="outline"
                                        onClick={() => setIsDownloadModalOpen(true)}
                                        className="gap-2"
                                        disabled={!formType}
                                        title={!formType ? "트랙을 먼저 선택해주세요" : undefined}
                                    >
                                        <Download className="h-4 w-4" />
                                        다운로드
                                    </Button>
                                </>
                            }
                        />

                        {formType && (
                            <DownloadModal
                                isOpen={isDownloadModalOpen}
                                onClose={() => setIsDownloadModalOpen(false)}
                                formType={formType}
                                projectId={id}
                            />
                        )}

                        {/* AI 재생성 확인 모달 */}
                        <ConfirmModal
                            isOpen={regenerateModalOpen}
                            onClose={() => setRegenerateModalOpen(false)}
                            onConfirm={runDraftGeneration}
                            title="신청서 초안 재생성"
                            description={["이미 생성된 초안이 있습니다.", "초안을 다시 생성하시겠습니까?", "기존 초안은 새로운 결과로 대체됩니다."]}
                            confirmLabel="재생성"
                            cancelLabel="취소"
                        />

                        {/* 작성 완료 확인 모달 */}
                        <ConfirmModal
                            isOpen={completeModalOpen}
                            onClose={() => setCompleteModalOpen(false)}
                            onConfirm={confirmComplete}
                            title="신청서 작성 완료"
                            description={["신청서 작성을 완료하시겠습니까?", "대시보드로 이동합니다."]}
                            confirmLabel="완료"
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
                                runDraftGeneration()
                            }}
                            title="재분석 필요"
                            description={[
                                "이전 단계에서 재분석이 수행되었습니다.",
                                "현재 단계의 초안이 최신 상태가 아닐 수 있습니다.",
                                "초안을 다시 생성하시겠습니까?",
                            ]}
                            confirmLabel="재생성"
                            cancelLabel="기존 결과 유지"
                        />
                    </div>

                    {/* 오른쪽: 참고 패널 */}
                    <div className={isReferencePanelOpen ? "flex-1 min-w-0" : ""}>
                        <div className="sticky top-16">
                            <ReferencePanel
                                isOpen={isReferencePanelOpen}
                                onToggle={() => setIsReferencePanelOpen(!isReferencePanelOpen)}
                                approvalCases={similarCases}
                                regulations={regulations}
                                track={project?.track}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
