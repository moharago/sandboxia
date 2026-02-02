"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { WizardNavigation } from "@/components/features/wizard"
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileUpload } from "@/components/ui/file-upload"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import formData from "@/data/formData.json"
import { useServiceMutation } from "@/hooks/mutations/use-service-mutation"
import { useUIStore } from "@/stores/ui-store"
import type { Project } from "@/types/data/project"

interface ServiceFormProps {
    project: Project
    id: string
}

interface FormState {
    companyName: string
    serviceName: string
    description: string
    memo: string
    selectedFormType: string
    uploadedFiles: Record<string, File | null>
}

export function ServiceForm({ project, id }: ServiceFormProps) {
    const router = useRouter()
    const { devIsAnalyzed, devHasChanges } = useUIStore()

    const serviceMutation = useServiceMutation({
        onSuccess: () => {
            // TODO: Supabase에서 current_step 업데이트 후 이동
            router.push(`/projects/${id}/eligibility`)
        },
        onError: (error) => {
            alert(error.message || "서버 오류가 발생했습니다.")
        },
    })

    // projectData로 초기값 설정 (key로 리마운트되므로 useEffect 불필요)
    const [formState, setFormState] = useState<FormState>({
        companyName: project.company_name,
        serviceName: project.service_name || "",
        description: project.service_description || "",
        memo: "",
        selectedFormType: "counseling",
        uploadedFiles: {},
    })

    const updateField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
        setFormState((prev) => ({ ...prev, [field]: value }))
    }

    const { companyName, serviceName, description, memo, selectedFormType, uploadedFiles } = formState
    const selectedForm = formData.find((f) => f.id === selectedFormType)

    const handleFileChange = (appId: string, file: File | null) => {
        setFormState((prev) => ({
            ...prev,
            uploadedFiles: { ...prev.uploadedFiles, [appId]: file },
        }))
    }

    const isFormValid = (() => {
        if (!companyName.trim() || !serviceName.trim() || !description.trim()) {
            return false
        }
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
        const files: File[] = []
        if (selectedForm) {
            for (const app of selectedForm.application) {
                const file = uploadedFiles[app.id]
                if (file) {
                    files.push(file)
                }
            }
        }

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

                <WizardNavigation
                    onAnalyze={handleSave}
                    onNext={() => router.push(`/projects/${id}/eligibility`)}
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
