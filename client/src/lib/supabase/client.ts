import { createBrowserClient } from '@supabase/ssr'

// createBrowserClient는 내부적으로 싱글톤 패턴을 사용하므로
// 매번 호출해도 동일한 인스턴스를 반환합니다.
// 이렇게 하면 인증 상태도 자동으로 관리됩니다.

/**
 * Supabase 세션에서 access token을 가져오는 공용 유틸리티.
 * 토큰이 없으면 (미인증) Error를 throw합니다.
 */
export async function getAuthToken(): Promise<string> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()

    if (!session?.access_token) {
        throw new Error("로그인이 필요합니다.")
    }

    return session.access_token
}

export function createClient() {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!supabaseUrl) {
        throw new Error('Missing environment variable: NEXT_PUBLIC_SUPABASE_URL')
    }

    if (!supabaseAnonKey) {
        throw new Error('Missing environment variable: NEXT_PUBLIC_SUPABASE_ANON_KEY')
    }

    return createBrowserClient(supabaseUrl, supabaseAnonKey, {
        auth: {
            // navigator.locks 교착상태 방지: 5초 timeout 후 lock 없이 실행
            lock: async <R>(name: string, acquireTimeout: number, fn: () => Promise<R>): Promise<R> => {
                if (typeof navigator === 'undefined' || !navigator.locks) {
                    return await fn()
                }
                const ac = new AbortController()
                const timer = setTimeout(() => ac.abort(), acquireTimeout || 5000)
                try {
                    return await navigator.locks.request(name, { signal: ac.signal }, async () => {
                        clearTimeout(timer)
                        return await fn()
                    })
                } catch {
                    return await fn()
                }
            },
        },
    })
}