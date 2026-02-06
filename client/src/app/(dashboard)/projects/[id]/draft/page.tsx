"use client"

import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { DownloadModal } from "@/components/features/draft/DownloadModal"
import { FormSectionList } from "@/components/features/draft/FormSectionList"
import { ReferencePanel } from "@/components/features/draft/ReferencePanel"
import { WizardNavigation } from "@/components/features/wizard"
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay"
import { Button } from "@/components/ui/button"
import { useDraftGenerateMutation } from "@/hooks/mutations/use-draft-mutation"
import { useDraftQuery, draftKeys } from "@/hooks/queries/use-draft-query"
import { useProjectQuery } from "@/hooks/queries/use-projects-query"
import { useWizardStore, type FormType } from "@/stores/wizard-store"
import { TRACK_TO_FORM_ID, type Track } from "@/types/data/project"
import { useQueryClient } from "@tanstack/react-query"
import { AlertCircle, Download, Sparkles } from "lucide-react"
import { useRouter } from "next/navigation"
import { use, useState } from "react"

/** Track 타입 가드: TRACK_TO_FORM_ID에 존재하는 유효한 Track인지 확인 */
const isTrack = (value: string | null | undefined): value is Track =>
    value != null && Object.prototype.hasOwnProperty.call(TRACK_TO_FORM_ID, value)

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

    // 프로젝트에서 track 정보 조회
    const { data: project, isLoading: isLoadingProject } = useProjectQuery(id)

    // Supabase에서 초안 데이터 조회
    const { data: draftData, isLoading: isLoadingDraft } = useDraftQuery(id)

    // AI 초안 생성 mutation
    const draftMutation = useDraftGenerateMutation()

    // track → formType 변환 (런타임 타입 검증)
    const formType: FormType | null = isTrack(project?.track)
        ? TRACK_TO_FORM_ID[project.track]
        : null

    // application_draft.form_values를 그대로 initialValues로 사용
    const initialValues = draftData?.form_values

    // AI 초안 생성 핸들러
    const handleGenerateDraft = async () => {
        try {
            await draftMutation.mutateAsync({ project_id: id })
            // 성공 시 draft query invalidate하여 새 데이터 로드
            queryClient.invalidateQueries({ queryKey: draftKeys.byProject(id) })
        } catch (error) {
            const message = error instanceof Error ? error.message : "알 수 없는 오류"
            alert(`AI 초안 생성에 실패했습니다: ${message}`)
        }
    }

    const handleBack = () => {
        setCurrentStep(3)
        router.push(`/projects/${id}/track`)
    }

    const handleComplete = () => {
        markStepComplete(4)
        router.push("/dashboard")
    }

    // 데이터 로딩 중
    if (isLoadingProject || isLoadingDraft) {
        return <AILoadingOverlay message="저장된 초안을 불러오고 있습니다..." />
    }

    // AI 초안 생성 중
    if (draftMutation.isPending) {
        return <AILoadingOverlay message="AI 신청서 초안 생성 중" />
    }

    // track 정보 없음
    if (!project?.track) {
        return (
            <div className="py-6">
                <div className="container">
                    <div className="flex items-center justify-center min-h-[400px]">
                        <div className="text-center space-y-4">
                            <AlertCircle className="h-12 w-12 mx-auto text-amber-500" />
                            <h2 className="text-lg font-semibold">트랙이 선택되지 않았습니다</h2>
                            <p className="text-muted-foreground">
                                이전 단계(트랙 선택)에서 트랙을 선택해주세요.
                            </p>
                            <button
                                type="button"
                                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
                                onClick={() => router.push(`/projects/${id}/track`)}
                            >
                                이전 단계로 돌아가기
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // 초안 데이터 있는지 여부 (빈 객체 {}는 false로 처리)
    const hasDraftData =
        !!draftData?.form_values &&
        typeof draftData.form_values === "object" &&
        Object.keys(draftData.form_values).length > 0

    return (
        <div className="py-6">
            <div className="container">
                <div className="flex gap-4">
                    {/* 왼쪽: 폼 영역 */}
                    <div className={isReferencePanelOpen ? "flex-[2] space-y-6" : "flex-1 space-y-6"}>
                        <div>
                            <h1 className="text-2xl font-bold mb-2">신청서 작성</h1>
                            <p className="text-muted-foreground">
                                {hasDraftData
                                    ? "AI가 생성한 초안을 검토하고 수정하세요"
                                    : "AI 초안 생성 버튼을 눌러 신청서 초안을 생성하세요"}
                            </p>
                        </div>

                        {hasDraftData ? (
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
                                <Button onClick={handleGenerateDraft} className="gap-2">
                                    <Sparkles className="h-4 w-4" />
                                    AI 초안 생성
                                </Button>
                            </div>
                        )}

                        {/* 동적 폼 필드 카드 */}
                        {formType ? (
                            <FormSectionList formType={formType} initialValues={initialValues} projectId={id} />
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">폼 타입을 확인할 수 없습니다.</div>
                        )}

                        <WizardNavigation
                            onBack={handleBack}
                            onNext={handleComplete}
                            nextLabel="작성 완료"
                            isAnalyzed={hasDraftData}
                            extraButtons={
                                <>
                                    {hasDraftData && (
                                        <Button variant="outline" onClick={handleGenerateDraft} className="gap-2">
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
                            <DownloadModal isOpen={isDownloadModalOpen} onClose={() => setIsDownloadModalOpen(false)} formType={formType} />
                        )}
                    </div>

                    {/* 오른쪽: 참고 패널 */}
                    <div className={isReferencePanelOpen ? "flex-1" : ""}>
                        <div className="sticky top-16">
                            <ReferencePanel isOpen={isReferencePanelOpen} onToggle={() => setIsReferencePanelOpen(!isReferencePanelOpen)} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
