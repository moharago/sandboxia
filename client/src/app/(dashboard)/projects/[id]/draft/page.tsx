"use client"

import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { DownloadModal } from "@/components/features/draft/DownloadModal"
import { FormSectionList } from "@/components/features/draft/FormSectionList"
import { ReferencePanel } from "@/components/features/draft/ReferencePanel"
import { WizardNavigation } from "@/components/features/wizard"
import { Button } from "@/components/ui/button"
import { useWizardStore } from "@/stores/wizard-store"
import { Download } from "lucide-react"
import { useRouter } from "next/navigation"
import { use, useState } from "react"

interface DraftPageProps {
    params: Promise<{ id: string }>
}

export default function DraftPage({ params }: DraftPageProps) {
    const { id } = use(params)
    const router = useRouter()

    const { markStepComplete, setCurrentStep, selectedFormType } = useWizardStore()
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false)

    const handleBack = () => {
        setCurrentStep(3)
        router.push(`/projects/${id}/track`)
    }

    const handleComplete = () => {
        markStepComplete(4)
        router.push("/dashboard")
    }

    return (
        <div className="py-6">
            <div className="container">
                <div className="flex gap-4">
                    {/* 왼쪽: 폼 영역 */}
                    <div className={isReferencePanelOpen ? "flex-[2] space-y-6" : "flex-1 space-y-6"}>
                        <div>
                            <h1 className="text-2xl font-bold mb-2">신청서 작성</h1>
                            <p className="text-muted-foreground">AI가 생성한 초안을 검토하고 수정하세요</p>
                        </div>

                        <AIAnalysisCard title="AI 초안 생성 완료" summary="AI가 제안하는 관련 문서를 우측 패널에서 확인하세요." />

                        {/* 동적 폼 필드 카드 */}
                        {selectedFormType ? (
                            <FormSectionList formType={selectedFormType} />
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">폼 타입을 선택해주세요.</div>
                        )}

                        <WizardNavigation
                            onBack={handleBack}
                            onNext={handleComplete}
                            nextLabel="작성 완료"
                            isAnalyzed={true}
                            extraButtons={
                                <Button variant="outline" onClick={() => setIsDownloadModalOpen(true)} className="gap-2">
                                    <Download className="h-4 w-4" />
                                    다운로드
                                </Button>
                            }
                        />

                        {selectedFormType && (
                            <DownloadModal isOpen={isDownloadModalOpen} onClose={() => setIsDownloadModalOpen(false)} formType={selectedFormType} />
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
