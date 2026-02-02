"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { User, AlertTriangle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Modal, ModalContent, ModalHeader, ModalFooter, ModalTitle, ModalDescription } from "@/components/ui/modal"
import { createClient } from "@/lib/supabase/client"
import { useAuthStore } from "@/stores/auth-store"
import { formatPhoneNumber, hasNonDigit } from "@/lib/utils/phone"

export default function MyAccountPage() {
    const router = useRouter()
    const supabase = createClient()
    const { user: authUser, profile, fetchProfile, isInitialized } = useAuthStore()

    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

    const [name, setName] = useState("")
    const [company, setCompany] = useState("")
    const [phone, setPhone] = useState("")
    const [phoneError, setPhoneError] = useState("")

    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
    const [confirmText, setConfirmText] = useState("")
    const [isDeleting, setIsDeleting] = useState(false)
    const [deleteError, setDeleteError] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const isConfirmValid = confirmText === profile?.name

    const handlePhoneChange = (value: string) => {
        if (hasNonDigit(value.replace(/-/g, ''))) {
            setPhoneError("숫자만 입력 가능합니다")
            setTimeout(() => setPhoneError(""), 2000)
            return
        }
        setPhoneError("")
        setPhone(formatPhoneNumber(value))
    }

    useEffect(() => {
        const loadProfile = async () => {
            // 초기화 완료 전이면 대기
            if (!isInitialized) return

            // 로그인 안 됨
            if (!authUser) {
                router.push('/login')
                return
            }

            try {
                await fetchProfile()
            } catch (err) {
                console.error('Failed to fetch profile:', err)
                setError('사용자 정보를 불러오는데 실패했습니다')
            }
            setLoading(false)
        }

        loadProfile()
    }, [authUser, router, fetchProfile, isInitialized])

    // profile이 없으면 (새 사용자) 온보딩으로 리다이렉트
    useEffect(() => {
        if (!loading && isInitialized && authUser && !profile) {
            router.push('/onboarding')
        }
    }, [loading, isInitialized, authUser, profile, router])

    useEffect(() => {
        if (profile) {
            setName(profile.name || "")
            setCompany(profile.company || "")
            setPhone(formatPhoneNumber(profile.phone || ""))
        }
    }, [profile])

    const handleSave = async () => {
        if (!name.trim()) {
            setSaveMessage({ type: 'error', text: '성명을 입력해주세요' })
            setTimeout(() => setSaveMessage(null), 3000)
            return
        }

        if (!authUser) {
            router.push('/login')
            return
        }

        setSaving(true)
        setSaveMessage(null)

        try {
            // Supabase 직접 호출
            const { error } = await supabase
                .from('users')
                .update({ name, company, phone })
                .eq('id', authUser.id)

            if (error) throw error

            await fetchProfile()
            setSaveMessage({ type: 'success', text: '저장되었습니다' })
        } catch (err) {
            console.error('Failed to save:', err)
            setSaveMessage({ type: 'error', text: '저장에 실패했습니다' })
        } finally {
            setSaving(false)
            setTimeout(() => setSaveMessage(null), 3000)
        }
    }

    const handleDeleteAccount = async () => {
        if (!isConfirmValid) return

        setIsDeleting(true)
        setDeleteError(null)

        try {
            const { data: { session } } = await supabase.auth.getSession()

            if (!session) {
                router.push('/login')
                return
            }

            // 계정 삭제는 서버 API 사용 (service_role 필요)
            const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
            const response = await fetch(`${apiBaseUrl}/api/users/me`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${session.access_token}`
                }
            })

            if (response.ok) {
                await supabase.auth.signOut()
                setIsDeleteModalOpen(false)
                router.push("/")
            } else {
                const error = await response.json()
                setDeleteError(error.detail || "삭제에 실패했습니다")
            }
        } catch (err) {
            console.error("Failed to delete account:", err)
            setDeleteError("삭제에 실패했습니다")
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

    if (loading || !isInitialized) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="p-6 flex flex-col items-center justify-center min-h-[400px] gap-4">
                <AlertTriangle className="h-12 w-12 text-destructive" />
                <p className="text-destructive font-medium">{error}</p>
                <Button variant="outline" onClick={() => window.location.reload()}>
                    다시 시도
                </Button>
            </div>
        )
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
                        <div className="space-y-2">
                            <Label htmlFor="email">이메일</Label>
                            <Input
                                id="email"
                                type="email"
                                value={profile?.email || ""}
                                disabled
                                className="bg-muted"
                            />
                            <p className="text-xs text-muted-foreground">이메일은 변경할 수 없습니다</p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">성명 *</Label>
                                <Input
                                    id="name"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="이름을 입력하세요"
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="company">회사명</Label>
                                <Input
                                    id="company"
                                    value={company}
                                    onChange={(e) => setCompany(e.target.value)}
                                    placeholder="회사명을 입력하세요"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="phone">연락처</Label>
                            <Input
                                id="phone"
                                type="tel"
                                value={phone}
                                onChange={(e) => handlePhoneChange(e.target.value)}
                                placeholder="010-0000-0000"
                            />
                            {phoneError && (
                                <p className="text-sm text-destructive">{phoneError}</p>
                            )}
                        </div>
                        <div className="flex items-center gap-3">
                            <Button onClick={handleSave} disabled={saving}>
                                {saving ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        저장 중...
                                    </>
                                ) : (
                                    "정보 저장"
                                )}
                            </Button>
                            {saveMessage && (
                                <span className={`text-sm ${saveMessage.type === 'success' ? 'text-green-600' : 'text-destructive'}`}>
                                    {saveMessage.text}
                                </span>
                            )}
                        </div>
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
                                삭제를 확인하려면 본인 이름 <strong>&quot;{profile?.name}&quot;</strong>을 입력하세요
                            </Label>
                            <Input
                                id="confirmDelete"
                                value={confirmText}
                                onChange={(e) => setConfirmText(e.target.value)}
                                placeholder={profile?.name || ""}
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
