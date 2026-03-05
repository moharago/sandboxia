"use client"

import { useState } from "react"
import { Download, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Modal, ModalContent, ModalHeader, ModalTitle } from "@/components/ui/modal"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { getAuthToken } from "@/lib/supabase/client"
import type { FormType } from "@/stores/wizard-store"
import { FORM_TYPE_LABELS } from "@/stores/wizard-store"
import formData from "@/data/formData.json"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

interface DownloadModalProps {
    isOpen: boolean
    onClose: () => void
    formType: FormType
    projectId: string
    /** 폼별 데이터 존재 여부 확인용 */
    formValues?: Record<string, unknown>
}

type FileFormat = "docx" | "pdf"

async function downloadFile(url: string, fallbackFilename: string) {
    const token = await getAuthToken()
    const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "다운로드에 실패했습니다.")
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get("Content-Disposition")
    const filenameMatch = contentDisposition?.match(/filename\*=UTF-8''(.+)/)
    const filename = filenameMatch ? decodeURIComponent(filenameMatch[1]) : fallbackFilename

    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
}

export function DownloadModal({ isOpen, onClose, formType, projectId, formValues }: DownloadModalProps) {
    const [fileFormat, setFileFormat] = useState<FileFormat>("docx")
    const [downloading, setDownloading] = useState<string | null>(null)
    const [isBulkDownloading, setIsBulkDownloading] = useState(false)

    const formMeta = formData.find((f) => f.type === formType)
    const applications = formMeta?.application || []

    // 폼에 데이터가 있는지 확인
    const hasFormData = (formId: string) => {
        if (!formValues) return false // formValues가 없으면 비활성화
        const formData = formValues[formId] as Record<string, unknown> | undefined
        if (!formData || typeof formData !== "object") return false
        // data 필드 안에 실제 내용이 있는지 확인 (서버 구조와 일치)
        const data = formData.data as Record<string, unknown> | undefined
        return data && typeof data === "object" && Object.keys(data).length > 0
    }

    // 다운로드 가능한 폼 목록
    const downloadableApps = applications.filter((app) => hasFormData(app.id))

    const handleDownload = async (formId: string, formName: string) => {
        setDownloading(formId)
        try {
            await downloadFile(
                `${API_BASE_URL}/api/v1/documents/${projectId}/${formId}/${fileFormat}`,
                `${formName}.${fileFormat}`
            )
        } catch (error) {
            console.error("다운로드 오류:", error)
            alert(error instanceof Error ? error.message : "다운로드에 실패했습니다.")
        } finally {
            setDownloading(null)
        }
    }

    const handleDownloadAll = async () => {
        if (downloadableApps.length === 0) {
            return
        }
        setIsBulkDownloading(true)
        const errors: string[] = []
        for (const app of downloadableApps) {
            try {
                await downloadFile(
                    `${API_BASE_URL}/api/v1/documents/${projectId}/${app.id}/${fileFormat}`,
                    `${app.name}.${fileFormat}`
                )
            } catch (error) {
                console.error(`다운로드 오류 (${app.name}):`, error)
                errors.push(app.name)
            }
        }
        setIsBulkDownloading(false)
        if (errors.length > 0) {
            alert(`다음 서류 다운로드에 실패했습니다: ${errors.join(", ")}`)
        }
    }

    return (
        <Modal open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <ModalContent className="max-w-md">
                <ModalHeader>
                    <ModalTitle>신청서 다운로드</ModalTitle>
                </ModalHeader>

                <div className="space-y-6">
                    <div className="space-y-3">
                        <p className="text-sm font-medium">파일 형식</p>
                        <div className="flex gap-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="fileFormat"
                                    value="docx"
                                    checked={fileFormat === "docx"}
                                    onChange={() => setFileFormat("docx")}
                                    className="h-4 w-4 text-primary accent-primary"
                                />
                                <span className="text-sm">DOCX</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    name="fileFormat"
                                    value="pdf"
                                    checked={fileFormat === "pdf"}
                                    onChange={() => setFileFormat("pdf")}
                                    className="h-4 w-4 text-primary accent-primary"
                                />
                                <span className="text-sm">PDF</span>
                            </label>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <p className="text-sm font-medium">{FORM_TYPE_LABELS[formType]} 서류</p>
                        <div className="space-y-2">
                            {applications.map((app) => {
                                const hasData = hasFormData(app.id)
                                const isDisabled = !hasData || isBulkDownloading || downloading === app.id

                                const button = (
                                    <Button
                                        key={app.id}
                                        variant="outline"
                                        className="w-full justify-start gap-2"
                                        onClick={() => handleDownload(app.id, app.name)}
                                        disabled={isDisabled}
                                    >
                                        {downloading === app.id ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Download className="h-4 w-4" />
                                        )}
                                        {app.name}
                                    </Button>
                                )

                                if (!hasData) {
                                    return (
                                        <TooltipProvider key={app.id}>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <span className="block">{button}</span>
                                                </TooltipTrigger>
                                                <TooltipContent>작성된 초안이 없습니다</TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    )
                                }

                                return button
                            })}
                        </div>
                    </div>

                    <Button
                        variant="gradient"
                        className="w-full gap-2"
                        onClick={handleDownloadAll}
                        disabled={isBulkDownloading || downloading !== null || downloadableApps.length === 0}
                    >
                        {isBulkDownloading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Download className="h-4 w-4" />
                        )}
                        일괄 다운로드
                    </Button>
                </div>
            </ModalContent>
        </Modal>
    )
}
