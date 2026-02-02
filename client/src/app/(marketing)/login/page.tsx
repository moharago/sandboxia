"use client"

import { useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { AlertCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { createClient } from "@/lib/supabase/client"

export default function LoginPage() {
    const router = useRouter()
    const supabase = createClient()
    const searchParams = useSearchParams()

    // URL 쿼리 파라미터에서 에러 확인 (초기값으로 설정)
    const errorParam = searchParams.get('error')
    const initialError = errorParam === 'auth_failed' ? '로그인에 실패했습니다. 다시 시도해주세요.' : null

    const [error, setError] = useState<string | null>(initialError)
    const [isLoading, setIsLoading] = useState(false)
    const [checking, setChecking] = useState(true)

    // 이미 로그인된 사용자는 대시보드로 리다이렉트
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const { data: { user }, error: authError } = await supabase.auth.getUser()

                if (authError) {
                    console.error('Auth check error:', authError)
                    setError('인증 확인 중 오류가 발생했습니다.')
                    return
                }

                if (user) {
                    router.push('/dashboard')
                    return
                }
            } catch (err) {
                console.error('Auth check failed:', err)
                setError('인증 확인 중 오류가 발생했습니다.')
            } finally {
                setChecking(false)
            }
        }
        checkAuth()
    }, [router, supabase])

    const handleGoogleLogin = async () => {
        setError(null)
        setIsLoading(true)

        const { error: authError } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/auth/callback`
            }
        })

        if (authError) {
            console.error('OAuth error:', authError)
            setError(authError.message || '로그인 중 오류가 발생했습니다')
            setIsLoading(false)
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
                        <CardTitle className="text-2xl">
                            <span className="text-gray-900">Sandbox</span>
                            <span className="text-teal-9">IA</span>
                        </CardTitle>
                        <CardDescription>규제 샌드박스 AI 컨설팅</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {error && (
                            <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}
                        <Button
                            onClick={handleGoogleLogin}
                            variant="outline"
                            className="w-full h-12 text-base flex items-center justify-center gap-3"
                            disabled={isLoading}
                        >
                            <svg className="w-5 h-5" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            {isLoading ? '로그인 중...' : 'Google로 시작하기'}
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}