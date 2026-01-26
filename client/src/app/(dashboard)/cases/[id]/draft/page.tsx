"use client"

import { use, useState } from "react"
import { useRouter } from "next/navigation"
import { notFound } from "next/navigation"
import { ArrowLeft, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AIAnalysisCard } from "@/components/features/analysis/AIAnalysisCard"
import { cases } from "@/data"
import { useWizardStore } from "@/stores/wizard-store"
import { FormSectionList } from "@/components/features/draft/FormSectionList"
import { ReferencePanel } from "@/components/features/draft/ReferencePanel"
import { DownloadModal } from "@/components/features/draft/DownloadModal"

interface DraftPageProps {
    params: Promise<{ id: string }>
}

export default function DraftPage({ params }: DraftPageProps) {
    const { id } = use(params)
    const router = useRouter()
    const caseData = cases.find((c) => c.id === id)

    const { markStepComplete, setCurrentStep, selectedFormType } = useWizardStore()
    const [isReferencePanelOpen, setIsReferencePanelOpen] = useState(true)
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false)

    if (!caseData) {
        notFound()
    }

    const handleBack = () => {
        setCurrentStep(3)
        router.push(`/cases/${id}/track`)
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

                        <AIAnalysisCard
                            title="AI 초안 생성 완료"
                            summary="AI가 제안하는 관련 문서를 우측 패널에서 확인하세요."
                        />

                        {/* 동적 폼 필드 카드 */}
                        <FormSectionList formType={selectedFormType} />

                        <div className="flex justify-between">
                            <Button variant="outline" onClick={handleBack} className="gap-2">
                                <ArrowLeft className="h-4 w-4" />
                                이전 단계
                            </Button>
                            <div className="flex gap-2">
                                <Button variant="outline" onClick={() => setIsDownloadModalOpen(true)} className="gap-2">
                                    <Download className="h-4 w-4" />
                                    다운로드
                                </Button>
                                <Button onClick={handleComplete} variant="gradient" className="gap-2">
                                    작성 완료
                                </Button>
                            </div>
                        </div>

                        <DownloadModal
                            isOpen={isDownloadModalOpen}
                            onClose={() => setIsDownloadModalOpen(false)}
                            formType={selectedFormType}
                        />
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
