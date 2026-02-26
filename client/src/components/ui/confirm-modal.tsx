"use client"

import { Button } from "@/components/ui/button"
import { Modal, ModalContent, ModalDescription, ModalFooter, ModalHeader, ModalTitle } from "@/components/ui/modal"
import { AlertTriangle } from "lucide-react"

interface ConfirmModalProps {
    /** 모달 열림 상태 */
    isOpen: boolean
    /** 모달 닫기 핸들러 */
    onClose: () => void
    /** 확인 버튼 클릭 핸들러 */
    onConfirm: () => void
    /** 모달 제목 */
    title: string
    /** 모달 설명 (여러 줄 가능) */
    description: string | string[]
    /** 확인 버튼 텍스트 */
    confirmLabel?: string
    /** 취소 버튼 텍스트 */
    cancelLabel?: string
    /** 확인 버튼 variant */
    confirmVariant?: "default" | "destructive"
    /** 로딩 상태 */
    isLoading?: boolean
}

export function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    description,
    confirmLabel = "확인",
    cancelLabel = "취소",
    confirmVariant = "default",
    isLoading = false,
}: ConfirmModalProps) {
    const descriptions = Array.isArray(description) ? description : [description]

    return (
        <Modal open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <ModalContent>
                <ModalHeader>
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
                            <AlertTriangle className="h-5 w-5 text-amber-600" />
                        </div>
                        <ModalTitle>{title}</ModalTitle>
                    </div>
                </ModalHeader>
                <ModalDescription asChild>
                    <div className="space-y-2 text-sm text-muted-foreground">
                        {descriptions.map((desc, idx) => (
                            <p key={idx}>{desc}</p>
                        ))}
                    </div>
                </ModalDescription>
                <ModalFooter className="mt-4">
                    <Button variant="outline" onClick={onClose} disabled={isLoading}>
                        {cancelLabel}
                    </Button>
                    <Button variant={confirmVariant} onClick={onConfirm} disabled={isLoading}>
                        {isLoading ? "처리 중..." : confirmLabel}
                    </Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    )
}
