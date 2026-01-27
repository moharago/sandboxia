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
import { useUserStore } from "@/stores/user-store"
import { useUIStore } from "@/stores/ui-store"
import { formatPhoneNumber, hasNonDigit } from "@/lib/utils/phone"

const DELETE_CONFIRMATION_TEXT = "삭제"

interface UserData {
    id: string
    email: string
    name: string | null
    company: string | null
    phone: string | null
    status: string
}

export default function MyAccountPage() {
    const router = useRouter()
    const supabase = createClient()
    const updateUserStore = useUserStore((state) => state.updateUser)
    const userFromStore = useUserStore((state) => state.user)
    const { devMode, isAuthenticated } = useUIStore()

    const [user, setUser] = useState<UserData | null>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

    const [name, setName] = useState("")
    const [company, setCompany] = useState("")
    const [phone, setPhone] = useState("")
    const [phoneError, setPhoneError] = useState("")

    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
    const [apiError, setApiError] = useState<string | null>(null)

    const handlePhoneChange = (value: string) => {
        if (hasNonDigit(value.replace(/-/g, ''))) {
            setPhoneError("숫자만 입력 가능합니다")
            setTimeout(() => setPhoneError(""), 2000)
            return
        }
        setPhoneError("")
        setPhone(formatPhoneNumber(value))
    }
    const [confirmText, setConfirmText] = useState("")
    const [isDeleting, setIsDeleting] = useState(false)
    const [deleteError, setDeleteError] = useState<string | null>(null)

    const isConfirmValid = confirmText === DELETE_CONFIRMATION_TEXT

    useEffect(() => {
        // devMode + 임시 로그인 상태면 user-store 데이터 사용
        if (devMode && isAuthenticated && userFromStore) {
            setUser({
                id: 'dev-user',
                email: userFromStore.email || 'hong@company.com',
                name: userFromStore.name || '홍길동',
                company: userFromStore.company || '스마트모빌리티',
                phone: userFromStore.phone || '010-1234-5678',
                status: 'ACTIVE'
            })
            setName(userFromStore.name || '홍길동')
            setCompany(userFromStore.company || '스마트모빌리티')
            setPhone(formatPhoneNumber(userFromStore.phone || '010-1234-5678'))
            setLoading(false)
            return
        }

        const fetchUser = async () => {
            const { data: { session } } = await supabase.auth.getSession()

            if (!session) {
                router.push('/login')
                return
            }

            try {
                const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
                const response = await fetch(`${apiBaseUrl}/api/users/me`, {
                    headers: {
                        'Authorization': `Bearer ${session.access_token}`
                    }
                })

                if (response.ok) {
                    const userData: UserData = await response.json()
                    setUser(userData)
                    setName(userData.name || "")
                    setCompany(userData.company || "")
                    setPhone(formatPhoneNumber(userData.phone || ""))
                } else {
                    // 에러 응답 처리
                    let errorMessage = '사용자 정보를 불러오는데 실패했습니다'
                    try {
                        const errorData = await response.json()
                        errorMessage = errorData.detail || errorData.message || errorMessage
                    } catch {
                        errorMessage = await response.text() || errorMessage
                    }
                    setApiError(errorMessage)
                }
            } catch (error) {
                console.error('Failed to fetch user:', error)
                setApiError('서버에 연결할 수 없습니다')
            } finally {
                setLoading(false)
            }
        }

        fetchUser()
    }, [router, supabase.auth, devMode, isAuthenticated, userFromStore])

    const handleSave = async () => {
        // devMode일 때는 실제 저장 불가
        if (devMode && isAuthenticated) {
            setSaveMessage({ type: 'error', text: '개발 모드에서는 저장할 수 없습니다' })
            setTimeout(() => setSaveMessage(null), 3000)
            return
        }

        // 성명 필수 체크
        if (!name.trim()) {
            setSaveMessage({ type: 'error', text: '성명을 입력해주세요' })
            setTimeout(() => setSaveMessage(null), 3000)
            return
        }

        setSaving(true)
        setSaveMessage(null)

        try {
            const { data: { session } } = await supabase.auth.getSession()

            if (!session) {
                router.push('/login')
                return
            }

            const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
            const response = await fetch(`${apiBaseUrl}/api/users/me`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`
                },
                body: JSON.stringify({ name, company, phone })
            })

            if (response.ok) {
                setUser(prev => prev ? { ...prev, name, company, phone } : null)
                updateUserStore({ name, company, phone })
                setSaveMessage({ type: 'success', text: '저장되었습니다' })
            } else {
                setSaveMessage({ type: 'error', text: '저장에 실패했습니다' })
            }
        } catch (error) {
            console.error('Failed to save:', error)
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
        } catch (error) {
            console.error("Failed to delete account:", error)
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

    if (loading) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    if (apiError) {
        return (
            <div className="p-6 flex flex-col items-center justify-center min-h-[400px] gap-4">
                <AlertTriangle className="h-12 w-12 text-destructive" />
                <p className="text-destructive font-medium">{apiError}</p>
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
                                value={user?.email || ""}
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
