"use client"

import { use, useState } from "react"
import { useRouter } from "next/navigation"
import { notFound } from "next/navigation"
import { WizardNavigation } from "@/components/features/wizard"
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FileUpload } from "@/components/ui/file-upload"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { cases } from "@/data"
import { useUIStore } from "@/stores/ui-store"
import { useWizardStore } from "@/stores/wizard-store"
import { useServiceMutation } from "@/hooks/mutations/use-service-mutation"
import formData from "@/data/formData.json"

interface ServicePageProps {
    params: Promise<{ id: string }>
}

export default function ServicePage({ params }: ServicePageProps) {
    const { id } = use(params)
    const router = useRouter()
    const caseData = cases.find((c) => c.id === id)

    const { setServiceData, markStepComplete, setCurrentStep } = useWizardStore()
    const { devIsAnalyzed, devHasChanges } = useUIStore()

    // 폼 상태를 하나의 객체로 통합 관리
    interface FormState {
        companyName: string
        serviceName: string
        description: string
        memo: string
        selectedFormType: string
        uploadedFiles: Record<string, File | null>
    }

    const getInitialFormState = (): FormState => ({
        companyName: caseData?.company || "",
        serviceName: caseData?.service || "",
        description: caseData?.description || "",
        memo: "",
        selectedFormType: "counseling",
        uploadedFiles: {},
    })

    const [formState, setFormState] = useState<FormState>(getInitialFormState)

    // 개별 필드 업데이트 헬퍼
    const updateField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
        setFormState((prev) => ({ ...prev, [field]: value }))
    }

    // 편의를 위한 destructuring
    const { companyName, serviceName, description, memo, selectedFormType, uploadedFiles } = formState

    const selectedForm = formData.find((f) => f.id === selectedFormType)

    const handleFileChange = (appId: string, file: File | null) => {
        setFormState((prev) => ({
            ...prev,
            uploadedFiles: { ...prev.uploadedFiles, [appId]: file },
        }))
    }

    // 케이스 변경 추적
    const [prevId, setPrevId] = useState(id)

    // 케이스가 변경되면 모든 폼 상태를 해당 케이스의 데이터로 초기화 (렌더링 중 조건부 업데이트)
    if (id !== prevId && caseData) {
        setPrevId(id)
        setFormState({
            companyName: caseData.company,
            serviceName: caseData.service,
            description: caseData.description || "",
            memo: "",
            selectedFormType: "counseling",
            uploadedFiles: {},
        })
    }

    if (!caseData) {
        notFound()
    }

    // 서비스 파싱 mutation
    const serviceMutation = useServiceMutation({
        onSuccess: () => {
            // Save form data to wizard store
            setServiceData({
                companyName,
                serviceName,
                description,
                memo,
            })

            markStepComplete(1)
            setCurrentStep(2)
            router.push(`/cases/${id}/market`)
        },
        onError: (error) => {
            alert(error.message || "서버 오류가 발생했습니다.")
        },
    })

    // 필수 필드 유효성 검사
    const isFormValid = (() => {
        // 기본 필드 검사
        if (!companyName.trim() || !serviceName.trim() || !description.trim()) {
            return false
        }

        // 신청서 파일 검사 (선택된 유형의 모든 파일이 업로드되었는지)
        if (selectedForm) {
            for (const app of selectedForm.application) {
                if (!uploadedFiles[app.id]) {
                    return false
                }
            }
        }

        return true
    })()

    const handleSave = () => {
        // 업로드된 파일들을 순서대로 수집
        const files: File[] = []
        if (selectedForm) {
            for (const app of selectedForm.application) {
                const file = uploadedFiles[app.id]
                if (file) {
                    files.push(file)
                }
            }
        }

        // mutation 실행
        serviceMutation.mutate({
            sessionId: id,
            requestedTrack: selectedFormType,
            consultantInput: {
                company_name: companyName,
                service_name: serviceName,
                service_description: description,
                additional_memo: memo,
            },
            files,
        })
    }

    return (
        <div className="py-6">
            {serviceMutation.isPending && <AILoadingOverlay />}
            <div className="container mx-auto px-4 space-y-6">
                <div>
                    <h1 className="text-2xl font-bold mb-2">기업 정보 입력</h1>
                    <p className="text-muted-foreground">기업과 서비스에 대한 기본 정보를 입력해주세요</p>
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>서비스 정보</CardTitle>
                        <CardDescription>규제 샌드박스 신청을 위한 서비스 기본 정보를 입력합니다</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="company">
                                    회사명 <span className="text-red-500">*</span>
                                </Label>
                                <Input id="company" value={companyName} onChange={(e) => updateField("companyName", e.target.value)} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="service">
                                    서비스명 <span className="text-red-500">*</span>
                                </Label>
                                <Input id="service" value={serviceName} onChange={(e) => updateField("serviceName", e.target.value)} />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="description">
                                서비스 설명 <span className="text-red-500">*</span>
                            </Label>
                            <Textarea
                                id="description"
                                placeholder="서비스에 대해 상세히 설명해주세요"
                                rows={4}
                                value={description}
                                onChange={(e) => updateField("description", e.target.value)}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="memo">추가 메모</Label>
                            <Textarea
                                id="memo"
                                placeholder="추가로 기록할 내용이 있다면 작성해주세요"
                                rows={3}
                                value={memo}
                                onChange={(e) => updateField("memo", e.target.value)}
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>신청 유형 선택 및 신청서 업로드</CardTitle>
                        <CardDescription>상담신청, 신속확인, 임시허가, 실증특례 중 하나를 선택하고 신청서를 업로드하세요</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-x-6 gap-y-2">
                            {formData.map((form) => (
                                <label key={form.id} className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="formType"
                                        value={form.id}
                                        checked={selectedFormType === form.id}
                                        onChange={(e) => updateField("selectedFormType", e.target.value)}
                                        className="h-4 w-4 text-primary accent-primary"
                                    />
                                    <span className="text-sm">{form.name}</span>
                                </label>
                            ))}
                        </div>
                    </CardContent>

                    {selectedForm && (
                        <CardContent className="space-y-4">
                            {selectedForm.application.map((app) => (
                                <div key={app.id} className="space-y-2">
                                    <Label>
                                        {app.name} <span className="text-red-500">*</span>
                                    </Label>
                                    <FileUpload value={uploadedFiles[app.id] ?? null} onChange={(file) => handleFileChange(app.id, file)} />
                                </div>
                            ))}
                        </CardContent>
                    )}
                </Card>

                {/* TODO: isAnalyzed는 나중에 projects.canonical 또는 project_files 존재 여부로 판단 */}
                {/* TODO: hasChanges는 현재 폼 데이터와 DB 저장된 데이터 비교로 판단 */}
                <WizardNavigation
                    onAnalyze={handleSave}
                    onNext={() => {
                        // 분석 완료 상태에서 다음 단계로 이동 (재분석 없이)
                        setServiceData({
                            companyName,
                            serviceName,
                            description,
                            memo,
                        })
                        markStepComplete(1)
                        setCurrentStep(2)
                        router.push(`/cases/${id}/market`)
                    }}
                    analyzeLabel="AI 분석 및 다음 단계"
                    nextLabel="다음 단계"
                    isAnalyzed={devIsAnalyzed}
                    hasChanges={devHasChanges}
                    isLoading={serviceMutation.isPending}
                    isAnalyzeDisabled={!isFormValid}
                />
            </div>
        </div>
    )
}
