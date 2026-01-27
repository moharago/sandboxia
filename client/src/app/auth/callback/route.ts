import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get('code')

    if (code) {
        const supabase = await createClient()
        const { data, error } = await supabase.auth.exchangeCodeForSession(code)

        if (!error && data.session) {
            // 유저 상태 확인
            try {
                const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
                const response = await fetch(`${apiBaseUrl}/api/users/me`, {
                    headers: {
                        'Authorization': `Bearer ${data.session.access_token}`
                    }
                })

                if (response.ok) {
                    const user = await response.json()

                    if (user.status === 'PENDING') {
                        return NextResponse.redirect(`${origin}/onboarding`)
                    } else {
                        return NextResponse.redirect(`${origin}/dashboard`)
                    }
                } else {
                    // 유저 정보 없음 → onboarding
                    return NextResponse.redirect(`${origin}/onboarding`)
                }
            } catch (e) {
                // API 호출 실패 시 onboarding으로
                console.error('Failed to fetch user:', e)
                return NextResponse.redirect(`${origin}/onboarding`)
            }
        }
    }

    // 에러 발생 시 로그인 페이지로
    return NextResponse.redirect(`${origin}/login?error=auth_failed`)
}
