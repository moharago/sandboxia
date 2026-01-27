"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { createClient } from "@/lib/supabase/client"
import { formatPhoneNumber, hasNonDigit } from "@/lib/utils/phone"

export default function OnboardingPage() {
    const router = useRouter()
    const supabase = createClient()

    const [name, setName] = useState("")
    const [company, setCompany] = useState("")
    const [phone, setPhone] = useState("")
    const [phoneError, setPhoneError] = useState("")
    const [loading, setLoading] = useState(false)
    const [checking, setChecking] = useState(true)

    const handlePhoneChange = (value: string) => {
        if (hasNonDigit(value.replace(/-/g, ''))) {
            setPhoneError("숫자만 입력 가능합니다")
            setTimeout(() => setPhoneError(""), 2000)
            return
        }
        setPhoneError("")
        setPhone(formatPhoneNumber(value))
    }

    // 이미 ACTIVE인 유저는 대시보드로 리디렉션
    useEffect(() => {
        const checkStatus = async () => {
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
                    const userData = await response.json()
                    if (userData.status === 'ACTIVE') {
                        router.push('/dashboard')
                        return
                    }
                }
            } catch {
                // 서버 연결 실패 시 무시하고 onboarding 진행
            } finally {
                setChecking(false)
            }
        }

        checkStatus()
    }, [router, supabase.auth])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)

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
                body: JSON.stringify({
                    name,
                    company,
                    phone,
                    status: 'ACTIVE'
                })
            })

            if (response.ok) {
                router.push('/dashboard')
            }
        } catch (error) {
            console.error(error)
        } finally {
            setLoading(false)
        }
    }

    if (checking) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        )
    }

    return (
        <div className="container mx-auto px-4 py-12">
            <div className="max-w-md mx-auto">
                <Card>
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl">추가 정보 입력</CardTitle>
                        <CardDescription>서비스 이용을 위해 정보를 입력해주세요</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">성명 *</Label>
                                <Input
                                    id="name"
                                    placeholder="이름을 입력하세요"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="company">회사명 (선택)</Label>
                                <Input
                                    id="company"
                                    placeholder="회사명을 입력하세요"
                                    value={company}
                                    onChange={(e) => setCompany(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="phone">연락처 (선택)</Label>
                                <Input
                                    id="phone"
                                    placeholder="010-0000-0000"
                                    value={phone}
                                    onChange={(e) => handlePhoneChange(e.target.value)}
                                />
                                {phoneError && (
                                    <p className="text-sm text-destructive">{phoneError}</p>
                                )}
                            </div>
                            <Button 
                                type="submit" 
                                className="w-full" 
                                variant="gradient"
                                disabled={loading}
                            >
                                {loading ? "처리 중..." : "시작하기"}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}