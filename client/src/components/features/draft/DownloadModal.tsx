"use client"

import { useState } from "react"
import { Download, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Modal, ModalContent, ModalHeader, ModalTitle } from "@/components/ui/modal"
import type { FormType } from "@/stores/wizard-store"
import { FORM_TYPE_LABELS } from "@/stores/wizard-store"
import formData from "@/data/formData.json"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

interface DownloadModalProps {
    isOpen: boolean
    onClose: () => void
    formType: FormType
    projectId: string
}

type FileFormat = "docx" | "pdf"

async function downloadFile(url: string, fallbackFilename: string) {
    const response = await fetch(url)
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

export function DownloadModal({ isOpen, onClose, formType, projectId }: DownloadModalProps) {
    const [fileFormat, setFileFormat] = useState<FileFormat>("docx")
    const [downloading, setDownloading] = useState<string | null>(null)
    const [isBulkDownloading, setIsBulkDownloading] = useState(false)

    const formMeta = formData.find((f) => f.type === formType)
    const applications = formMeta?.application || []

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
        setIsBulkDownloading(true)
        try {
            await downloadFile(
                `${API_BASE_URL}/api/v1/documents/${projectId}/zip?format=${fileFormat}`,
                "신청서류.zip"
            )
        } catch (error) {
            console.error("일괄 다운로드 오류:", error)
            alert(error instanceof Error ? error.message : "다운로드에 실패했습니다.")
        } finally {
            setIsBulkDownloading(false)
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
                            {applications.map((app) => (
                                <Button
                                    key={app.id}
                                    variant="outline"
                                    className="w-full justify-start gap-2"
                                    onClick={() => handleDownload(app.id, app.name)}
                                    disabled={isBulkDownloading || downloading === app.id}
                                >
                                    {downloading === app.id ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Download className="h-4 w-4" />
                                    )}
                                    {app.name}
                                </Button>
                            ))}
                        </div>
                    </div>

                    <Button
                        variant="gradient"
                        className="w-full gap-2"
                        onClick={handleDownloadAll}
                        disabled={isBulkDownloading || downloading !== null}
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
