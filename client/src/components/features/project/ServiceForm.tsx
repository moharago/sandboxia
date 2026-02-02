"use client"

import { WizardNavigation } from "@/components/features/wizard"
import { AILoadingOverlay } from "@/components/ui/ai-loading-overlay"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FileUpload } from "@/components/ui/file-upload"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import formData from "@/data/formData.json"
import { useServiceMutation } from "@/hooks/mutations/use-service-mutation"
import { useProjectFilesQuery } from "@/hooks/queries/use-projects-query"
import { useUIStore } from "@/stores/ui-store"
import { DEFAULT_TRACK, FORM_ID_TO_TRACK, TRACK_TO_FORM_ID, type Project, type Track } from "@/types/data/project"
import { FileText } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"

interface ServiceFormProps {
    project: Project
    id: string
}

interface FormState {
    companyName: string
    serviceName: string
    description: string
    memo: string
    /** 선택된 트랙 (counseling/quick_check/temp_permit/demo) */
    selectedTrack: Track
    uploadedFiles: Record<string, File | null>
}

export function ServiceForm({ project, id }: ServiceFormProps) {
    const router = useRouter()
    const { devIsAnalyzed, devHasChanges } = useUIStore()

    // 이미 분석 완료된 경우 (current_step >= 2) 업로드된 파일 목록 조회
    const isAnalysisCompleted = project.current_step >= 2
    const { data: uploadedFileList } = useProjectFilesQuery(id)

    const serviceMutation = useServiceMutation({
        onSuccess: () => {
            router.push(`/projects/${id}/eligibility`)
        },
        onError: (error) => {
            alert(error.message || "서버 오류가 발생했습니다.")
        },
    })

    // 저장된 트랙 (DB 값 그대로 사용, 없으면 counseling=상담신청)
    const savedTrack: Track = project.track ?? "counseling"

    // projectData로 초기값 설정 (key로 리마운트되므로 useEffect 불필요)
    const [formState, setFormState] = useState<FormState>({
        companyName: project.company_name,
        serviceName: project.service_name || "",
        description: project.service_description || "",
        memo: project.additional_notes || "",
        selectedTrack: savedTrack,
        uploadedFiles: {},
    })

    const updateField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
        setFormState((prev) => ({ ...prev, [field]: value }))
    }

    const { companyName, serviceName, description, memo, selectedTrack, uploadedFiles } = formState
    // selectedTrack을 formData의 id(문자열)로 변환하여 찾기
    const selectedFormId = TRACK_TO_FORM_ID[selectedTrack]
    const selectedForm = formData.find((f) => f.id === selectedFormId)

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
        // 신청서 업로드 폼에 파일이 업로드되어야 유효
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
            requestedTrack: selectedTrack,
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
                            {formData.map((form) => {
                                const trackValue = FORM_ID_TO_TRACK[form.id] ?? DEFAULT_TRACK
                                return (
                                    <label key={form.id} className="flex items-center gap-2 cursor-pointer">
                                        <input
                                            type="radio"
                                            name="formType"
                                            value={trackValue}
                                            checked={selectedTrack === trackValue}
                                            onChange={(e) => updateField("selectedTrack", e.target.value as Track)}
                                            className="h-4 w-4 text-primary accent-primary"
                                        />
                                        <span className="text-sm">{form.name}</span>
                                    </label>
                                )
                            })}
                        </div>
                    </CardContent>

                    {/* 기존에 저장된 파일이 있으면 표시 */}
                    {uploadedFileList && uploadedFileList.length > 0 && (
                        <CardContent className="space-y-4 pt-0">
                            <div className="space-y-2">
                                <Label className="text-muted-foreground">저장된 파일</Label>
                                <div className="space-y-2">
                                    {uploadedFileList.map((file) => (
                                        <div key={file.id} className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                                            <FileText className="h-4 w-4 text-muted-foreground" />
                                            <span className="text-sm">{file.file_name}</span>
                                            <span className="text-xs text-muted-foreground ml-auto">{file.file_type?.toUpperCase()}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    )}

                    {/* 파일 업로드 UI (항상 표시) */}
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
                    isAnalyzed={isAnalysisCompleted || devIsAnalyzed}
                    hasChanges={devHasChanges}
                    isLoading={serviceMutation.isPending}
                    isAnalyzeDisabled={!isFormValid}
                />
            </div>
        </div>
    )
}
