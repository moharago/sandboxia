"use client"

import { useState } from "react"
import type { ReactNode } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

interface QueryProviderProps {
    children: ReactNode
}

export function QueryProvider({ children }: QueryProviderProps) {
    const [client] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: Infinity, // 데이터는 mutation 성공 시 invalidate로만 갱신
                        gcTime: Infinity, // 세션 동안 캐시 유지 (step 이동 시 PageLoader 방지)
                        refetchOnWindowFocus: false,
                        refetchOnReconnect: false,
                    },
                },
            })
    )

    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
