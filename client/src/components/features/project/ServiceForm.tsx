"use client"

import { WizardNavigation } from "@/components/features/wizard"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ConfirmModal } from "@/components/ui/confirm-modal"
import { FileUpload } from "@/components/ui/file-upload"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import formData from "@/data/formData.json"
import { useEligibilityMutation } from "@/hooks/mutations/use-eligibility-mutation"
import { useServiceMutation } from "@/hooks/mutations/use-service-mutation"
import { useAgentNodesQuery } from "@/hooks/queries/use-agent-nodes-query"
import { useProjectFilesQuery } from "@/hooks/queries/use-projects-query"
import { useAgentProgress } from "@/hooks/streaming/use-agent-progress"
import { projectsApi, type ProjectFile } from "@/lib/api/projects"
import { PAGE_STEPS } from "@/lib/utils/step-utils"
import { useUIStore } from "@/stores/ui-store"
import { DEFAULT_TRACK, FORM_ID_TO_TRACK, TRACK_TO_FORM_ID, type Project, type Track } from "@/types/data/project"
import { useQueryClient } from "@tanstack/react-query"
import { Download, FileText } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

interface ServiceFormProps {
    project: Project
    id: string
}

interface FormState {
    companyName: string
    serviceName: string
    description: string
    memo: string
    selectedTrack: Track
    uploadedFiles: Record<string, File | null>
}

const PAGE_STEP = PAGE_STEPS.service // 1

export function ServiceForm({ project, id }: ServiceFormProps) {
    const router = useRouter()
    const queryClient = useQueryClient()
    const { devIsAnalyzed, devHasChanges, showGlobalAILoader, updateGlobalAILoader, hideGlobalAILoader } = useUIStore()

    // 현재 단계와 페이지 단계 비교
    const currentStep = project.current_step
    const isAheadOfCurrentStep = currentStep > PAGE_STEP // 이미 분석 완료된 상태
    const isAtCurrentStep = currentStep === PAGE_STEP // 현재 단계

    // 파일 목록 조회
    const { data: uploadedFileList } = useProjectFilesQuery(id)

    // 컴포넌트 마운트 시 전역 로더 숨기기
    useEffect(() => {
        hideGlobalAILoader()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // 에이전트 노드 목록 조회
    const { data: serviceNodes } = useAgentNodesQuery("service_structurer")
    const { data: eligibilityNodes } = useAgentNodesQuery("eligibility_evaluator")

    // SSE 진행 상태 구독 (전역 로더 자동 업데이트)
    const serviceProgress = useAgentProgress({
        projectId: id,
        useGlobalLoader: true,
        globalLoaderMessage: "서비스 정보 분석 중...",
        globalLoaderNodes: serviceNodes?.nodes,
    })
    const eligibilityProgress = useAgentProgress({
        projectId: id,
        useGlobalLoader: true,
        globalLoaderMessage: "서비스 규제 현황 분석 중...",
        globalLoaderNodes: eligibilityNodes?.nodes,
    })

    // 모달 상태
    const [reanalyzeModalOpen, setReanalyzeModalOpen] = useState(false)
    const [errorModalOpen, setErrorModalOpen] = useState(false)
    const [errorMessage, setErrorMessage] = useState("")

    // 에이전트 실행 상태 (어떤 에이전트 로딩 화면 보여줄지)
    const [runningAgent, setRunningAgent] = useState<"service" | "eligibility" | null>(null)

    // Mutations
    const serviceMutation = useServiceMutation({
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projects"] })
        },
        onError: (error) => {
            serviceProgress.unsubscribe()
            setRunningAgent(null)
            hideGlobalAILoader()
            setErrorMessage(error.message || "서비스 분석 중 오류가 발생했습니다.")
            setErrorModalOpen(true)
        },
    })

    const eligibilityMutation = useEligibilityMutation({
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["projects"] })
            queryClient.invalidateQueries({ queryKey: ["eligibility"] })
            setRunningAgent(null)
            // 전역 로더는 다음 페이지에서 숨김
            router.push(`/projects/${id}/eligibility`)
        },
        onError: (error) => {
            eligibilityProgress.unsubscribe()
            setRunningAgent(null)
            hideGlobalAILoader()
            setErrorMessage(`시장출시 진단 실패: ${error.message}`)
            setErrorModalOpen(true)
        },
    })

    // 폼 상태
    const savedTrack: Track = project.track ?? "counseling"
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
    const selectedFormId = TRACK_TO_FORM_ID[selectedTrack]
    const selectedForm = formData.find((f) => f.id === selectedFormId)

    const handleFileChange = (appId: string, file: File | null) => {
        setFormState((prev) => ({
            ...prev,
            uploadedFiles: { ...prev.uploadedFiles, [appId]: file },
        }))
    }

    const handleFileDownload = async (file: ProjectFile) => {
        try {
            const url = await projectsApi.getFileDownloadUrl(file)
            const link = document.createElement("a")
            link.href = url
            link.download = file.file_name
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
        } catch (error) {
            setErrorMessage(`파일 다운로드에 실패했습니다.\n${error instanceof Error ? error.message : ""}`)
            setErrorModalOpen(true)
        }
    }

    const isFormValid = (() => {
        if (!companyName.trim() || !serviceName.trim() || !description.trim()) return false
        if (selectedForm) {
            for (const app of selectedForm.application) {
                if (!uploadedFiles[app.id]) return false
            }
        }
        return true
    })()

    const getFiles = (): File[] => {
        const files: File[] = []
        if (selectedForm) {
            for (const app of selectedForm.application) {
                const file = uploadedFiles[app.id]
                if (file) files.push(file)
            }
        }
        return files
    }

    const getMutationPayload = () => ({
        sessionId: id,
        requestedTrack: selectedTrack,
        consultantInput: {
            company_name: companyName,
            service_name: serviceName,
            service_description: description,
            additional_memo: memo,
        },
        files: getFiles(),
    })

    // 서비스 분석만 실행 (재분석 - 페이지 이동 없음)
    const runServiceOnly = async () => {
        setReanalyzeModalOpen(false)
        try {
            // 재분석 시 current_step을 현재 페이지 단계(1)로 업데이트
            await projectsApi.updateStatus(id, project.status, PAGE_STEP)
            await queryClient.invalidateQueries({ queryKey: ["projects"] })
            setRunningAgent("service")
            serviceProgress.subscribe()
            serviceMutation.mutate(getMutationPayload(), {
                onSuccess: () => {
                    setRunningAgent(null)
                    hideGlobalAILoader() // 재분석 완료 시 로더 숨김
                    queryClient.invalidateQueries({ queryKey: ["projects"] })
                },
                onError: () => {
                    setRunningAgent(null)
                    hideGlobalAILoader()
                    queryClient.invalidateQueries({ queryKey: ["projects"] })
                },
            })
        } catch (error) {
            setRunningAgent(null)
            hideGlobalAILoader()
            const message = error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다."
            setErrorMessage(`서비스 분석 준비 중 오류가 발생했습니다: ${message}`)
            setErrorModalOpen(true)
            await queryClient.invalidateQueries({ queryKey: ["projects"] })
        }
    }

    // 서비스 + eligibility 순차 실행 후 이동
    const runServiceAndEligibility = () => {
        setRunningAgent("service")
        serviceProgress.subscribe()
        serviceMutation.mutate(getMutationPayload(), {
            onSuccess: () => {
                setRunningAgent("eligibility")
                // 전역 로더 메시지/노드 업데이트
                showGlobalAILoader({
                    message: "서비스 규제 현황 분석 중...",
                    nodes: eligibilityNodes?.nodes,
                    progress: 0,
                    completedNodes: [],
                    currentNodeId: null,
                })
                eligibilityProgress.subscribe()
                eligibilityMutation.mutate({ project_id: id })
            },
        })
    }

    // 다음 단계 버튼 클릭 (current_step > PAGE_STEP인 경우: 분석 없이 이동만)
    const handleNext = () => {
        // current_step > PAGE_STEP: 분석 없이 바로 이동
        router.push(`/projects/${id}/eligibility`)
    }

    // 재분석 버튼 클릭
    const handleReanalyze = () => {
        setReanalyzeModalOpen(true)
    }

    const isLoading = serviceMutation.isPending || eligibilityMutation.isPending || runningAgent !== null

    return (
        <div className="py-6">
            {/* 재분석 확인 모달 */}
            <ConfirmModal
                isOpen={reanalyzeModalOpen}
                onClose={() => setReanalyzeModalOpen(false)}
                onConfirm={runServiceOnly}
                title="서비스 분석 재실행"
                description={[
                    "이미 서비스 분석이 완료된 상태입니다.",
                    "다시 분석하시겠습니까?",
                    "기존 분석 결과는 새로운 결과로 대체되며, 이후 단계(시장출시 진단, 트랙 선택 등)도 재분석이 필요합니다.",
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
                                        <button
                                            key={file.id}
                                            type="button"
                                            onClick={() => handleFileDownload(file)}
                                            className="flex items-center gap-2 p-3 rounded-lg bg-muted/50 w-full hover:bg-muted transition-colors cursor-pointer text-left"
                                        >
                                            <FileText className="h-4 w-4 text-muted-foreground" />
                                            <span className="text-sm">{file.file_name}</span>
                                            <span className="text-xs text-muted-foreground ml-auto flex items-center gap-2">
                                                {file.file_type?.toUpperCase()}
                                                <Download className="h-3 w-3" />
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    )}

                    {/* 파일 업로드 UI */}
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
                    onAnalyze={isAtCurrentStep ? runServiceAndEligibility : undefined}
                    onReanalyze={isAheadOfCurrentStep ? handleReanalyze : undefined}
                    onNext={isAheadOfCurrentStep ? handleNext : undefined}
                    analyzeLabel="AI 분석 및 다음 단계"
                    nextLabel="다음 단계"
                    isAnalyzed={isAheadOfCurrentStep || devIsAnalyzed}
                    hasChanges={devHasChanges}
                    isLoading={isLoading}
                    isAnalyzeDisabled={!isFormValid}
                />
            </div>
        </div>
    )
}
