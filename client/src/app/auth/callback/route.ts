import { createClient } from "@/lib/supabase/server"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get("code")

    if (!code) {
        console.error("[auth/callback] No code provided in callback URL")
        return NextResponse.redirect(`${origin}/login?error=auth_failed`)
    }

    try {
        const supabase = await createClient()
        const { data, error } = await supabase.auth.exchangeCodeForSession(code)

        if (error) {
            console.error("[auth/callback] Failed to exchange code for session:", error.message)
            return NextResponse.redirect(`${origin}/login?error=auth_failed`)
        }

        if (!data.session) {
            console.error("[auth/callback] No session returned after code exchange")
            return NextResponse.redirect(`${origin}/login?error=auth_failed`)
        }

        // 유저 상태 확인
        const { data: userData, error: userError } = await supabase
            .from("users")
            .select("status")
            .eq("id", data.session.user.id)
            .single()

        if (userError) {
            // PGRST116: Row not found - 신규 유저
            if (userError.code === "PGRST116") {
                return NextResponse.redirect(`${origin}/onboarding`)
            }
            console.error("[auth/callback] Failed to fetch user status:", userError.message)
            return NextResponse.redirect(`${origin}/onboarding`)
        }

        if (userData?.status === "ACTIVE") {
            return NextResponse.redirect(`${origin}/dashboard`)
        }

        return NextResponse.redirect(`${origin}/onboarding`)
    } catch (err) {
        console.error("[auth/callback] Unexpected error:", err)
        return NextResponse.redirect(`${origin}/login?error=auth_failed`)
    }
}
