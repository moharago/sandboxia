"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Modal, ModalContent, ModalDescription, ModalFooter, ModalHeader, ModalTitle } from "@/components/ui/modal"
import { useDeleteProjectMutation } from "@/hooks/mutations/use-delete-project-mutation"
import { AlertTriangle } from "lucide-react"
import { useState } from "react"

interface DeleteProjectModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    projectId: string
    companyName: string
}

export function DeleteProjectModal({ open, onOpenChange, projectId, companyName }: DeleteProjectModalProps) {
    const [confirmText, setConfirmText] = useState("")
    const [error, setError] = useState<string | null>(null)

    const isConfirmValid = confirmText === companyName

    const { mutate: deleteProject, isPending: isDeleting } = useDeleteProjectMutation({
        onSuccess: () => {
            onOpenChange(false)
        },
        onError: (err) => {
            setError(err.message || "삭제에 실패했습니다")
        },
    })

    const handleClose = () => {
        if (isDeleting) return
        // 모달 닫을 때 상태 초기화
        setConfirmText("")
        setError(null)
        onOpenChange(false)
    }

    const handleDelete = () => {
        if (!isConfirmValid || isDeleting) return
        setError(null)
        deleteProject(projectId)
    }

    return (
        <Modal open={open} onOpenChange={handleClose}>
            <ModalContent>
                <ModalHeader>
                    <div className="flex items-center gap-2 text-destructive">
                        <AlertTriangle className="h-5 w-5" />
                        <ModalTitle>프로젝트 삭제</ModalTitle>
                    </div>
                    <ModalDescription className="pt-2">프로젝트를 삭제하면 모든 데이터가 영구적으로 삭제되며 복구할 수 없습니다.</ModalDescription>
                </ModalHeader>

                <div className="space-y-2 py-4">
                    <Label htmlFor="confirmDelete">
                        삭제를 확인하려면 기업명 <strong>&quot;{companyName}&quot;</strong>을 입력하세요
                    </Label>
                    <Input
                        id="confirmDelete"
                        value={confirmText}
                        onChange={(e) => setConfirmText(e.target.value)}
                        placeholder={companyName}
                        disabled={isDeleting}
                    />
                    {error && <p className="text-sm text-destructive">{error}</p>}
                </div>

                <ModalFooter>
                    <Button variant="outline" onClick={handleClose} disabled={isDeleting}>
                        취소
                    </Button>
                    <Button variant="destructive" onClick={handleDelete} disabled={!isConfirmValid || isDeleting}>
                        {isDeleting ? "삭제 중..." : "프로젝트 삭제"}
                    </Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    )
}
