"use client"

import { useState } from "react"
import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Modal, ModalContent, ModalHeader, ModalTitle } from "@/components/ui/modal"
import type { FormType } from "@/stores/wizard-store"
import { FORM_TYPE_LABELS } from "@/stores/wizard-store"
import formData from "@/data/formData.json"

interface DownloadModalProps {
    isOpen: boolean
    onClose: () => void
    formType: FormType
}

type FileFormat = "docx" | "pdf"

export function DownloadModal({ isOpen, onClose, formType }: DownloadModalProps) {
    const [fileFormat, setFileFormat] = useState<FileFormat>("docx")

    const formMeta = formData.find((f) => f.type === formType)
    const applications = formMeta?.application || []

    const handleDownload = (applicationId: string, applicationName: string) => {
        // TODO: 실제 다운로드 로직 구현
    }

    const handleDownloadAll = () => {
        // TODO: 일괄 다운로드 로직 구현
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
                                >
                                    <Download className="h-4 w-4" />
                                    {app.name}
                                </Button>
                            ))}
                        </div>
                    </div>

                    <Button variant="gradient" className="w-full gap-2" onClick={handleDownloadAll}>
                        <Download className="h-4 w-4" />
                        일괄 다운로드
                    </Button>
                </div>
            </ModalContent>
        </Modal>
    )
}
