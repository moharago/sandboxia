import { createBrowserClient } from '@supabase/ssr'

// createBrowserClient는 내부적으로 싱글톤 패턴을 사용하므로
// 매번 호출해도 동일한 인스턴스를 반환합니다.
// 이렇게 하면 인증 상태도 자동으로 관리됩니다.
export function createClient() {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!supabaseUrl) {
        throw new Error('Missing environment variable: NEXT_PUBLIC_SUPABASE_URL')
    }

    if (!supabaseAnonKey) {
        throw new Error('Missing environment variable: NEXT_PUBLIC_SUPABASE_ANON_KEY')
    }

    return createBrowserClient(supabaseUrl, supabaseAnonKey)
}