"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { User, Building2, Shield, Bell, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { ToggleSwitch } from "@/components/ui/toggle-switch"
import { Modal, ModalContent, ModalHeader, ModalFooter, ModalTitle, ModalDescription } from "@/components/ui/modal"
import { useUIStore } from "@/stores/ui-store"

const DELETE_CONFIRMATION_TEXT = "삭제"

export default function MyAccountPage() {
    const router = useRouter()
    const setAuthenticated = useUIStore((state) => state.setAuthenticated)
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
    const [confirmText, setConfirmText] = useState("")
    const [isDeleting, setIsDeleting] = useState(false)
    const [deleteError, setDeleteError] = useState<string | null>(null)

    const isConfirmValid = confirmText === DELETE_CONFIRMATION_TEXT

    const handleDeleteAccount = async () => {
        if (!isConfirmValid) return

        setIsDeleting(true)
        setDeleteError(null)
        try {
            // TODO: API call to delete account
            await new Promise((resolve) => setTimeout(resolve, 1000))

            setAuthenticated(false)
            setIsDeleteModalOpen(false)
            router.push("/")
        } catch (error) {
            console.error("Failed to delete account:", error)
            setDeleteError(error instanceof Error ? error.message : String(error))
        } finally {
            setIsDeleting(false)
        }
    }

    const handleModalClose = () => {
        if (isDeleting) return
        setIsDeleteModalOpen(false)
        setConfirmText("")
        setDeleteError(null)
    }
    return (
        <div className="p-6">
            <div className="max-w-2xl mx-auto space-y-6">
                <div>
                    <h1 className="text-2xl font-bold mb-2">마이페이지</h1>
                    <p className="text-muted-foreground">계정 정보를 관리하세요</p>
                </div>

                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <User className="h-5 w-5 text-muted-foreground" />
                            <CardTitle>기본 정보</CardTitle>
                        </div>
                        <CardDescription>계정의 기본 정보를 수정합니다</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">이름</Label>
                                <Input id="name" defaultValue="홍길동" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">이메일</Label>
                                <Input id="email" type="email" defaultValue="hong@company.com" />
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="phone">연락처</Label>
                                <Input id="phone" type="tel" defaultValue="010-1234-5678" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="position">직책</Label>
                                <Input id="position" defaultValue="대표이사" />
                            </div>
                        </div>
                        <Button>정보 저장</Button>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Shield className="h-5 w-5 text-muted-foreground" />
                            <CardTitle>보안 설정</CardTitle>
                        </div>
                        <CardDescription>비밀번호를 변경합니다</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="currentPassword">현재 비밀번호</Label>
                            <Input id="currentPassword" type="password" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="newPassword">새 비밀번호</Label>
                            <Input id="newPassword" type="password" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirmPassword">비밀번호 확인</Label>
                            <Input id="confirmPassword" type="password" />
                        </div>
                        <Button>비밀번호 변경</Button>
                    </CardContent>
                </Card>

                <Card className="border-destructive/20">
                    <CardHeader>
                        <CardTitle className="text-destructive">계정 삭제</CardTitle>
                        <CardDescription>계정을 삭제하면 모든 데이터가 영구적으로 삭제됩니다</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button variant="destructive" onClick={() => setIsDeleteModalOpen(true)}>
                            계정 삭제
                        </Button>
                    </CardContent>
                </Card>

                <Modal open={isDeleteModalOpen} onOpenChange={handleModalClose}>
                    <ModalContent>
                        <ModalHeader>
                            <div className="flex items-center gap-2 text-destructive">
                                <AlertTriangle className="h-5 w-5" />
                                <ModalTitle>계정 삭제</ModalTitle>
                            </div>
                            <ModalDescription className="pt-2">
                                계정을 삭제하면 모든 데이터가 영구적으로 삭제되며 복구할 수 없습니다. 정말 삭제하시겠습니까?
                            </ModalDescription>
                        </ModalHeader>

                        <div className="space-y-2 py-4">
                            <Label htmlFor="confirmDelete">
                                삭제를 확인하려면 <strong>&quot;{DELETE_CONFIRMATION_TEXT}&quot;</strong>를 입력하세요
                            </Label>
                            <Input
                                id="confirmDelete"
                                value={confirmText}
                                onChange={(e) => setConfirmText(e.target.value)}
                                placeholder={DELETE_CONFIRMATION_TEXT}
                                disabled={isDeleting}
                            />
                            {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}
                        </div>

                        <ModalFooter>
                            <Button variant="outline" onClick={handleModalClose} disabled={isDeleting}>
                                취소
                            </Button>
                            <Button variant="destructive" onClick={handleDeleteAccount} disabled={!isConfirmValid || isDeleting}>
                                {isDeleting ? "삭제 중..." : "계정 삭제"}
                            </Button>
                        </ModalFooter>
                    </ModalContent>
                </Modal>
            </div>
        </div>
    )
}
