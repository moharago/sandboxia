import { createClient } from "@/lib/supabase/server"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get("code")

    if (code) {
        const supabase = await createClient()
        const { data, error } = await supabase.auth.exchangeCodeForSession(code)

        if (!error && data.session) {
            // Supabase 직접 호출로 유저 상태 확인
            try {
                const { data: userData, error: userError } = await supabase.from("users").select("status").eq("id", data.session.user.id).single()
                if (userError) throw userError

                if (userData?.status === "ACTIVE") {
                    return NextResponse.redirect(`${origin}/dashboard`)
                } else {
                    return NextResponse.redirect(`${origin}/onboarding`)
                }
            } catch {
                // 유저 정보 없음 → onboarding
                return NextResponse.redirect(`${origin}/onboarding`)
            }
        }
    }

    // 에러 발생 시 로그인 페이지로
    return NextResponse.redirect(`${origin}/login?error=auth_failed`)
}
