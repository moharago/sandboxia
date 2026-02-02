"use client"

import { useAuthStore } from "@/stores/auth-store"
import type { ReactNode } from "react"
import { useEffect } from "react"

interface AuthProviderProps {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const initialize = useAuthStore((state) => state.initialize)
    const isInitialized = useAuthStore((state) => state.isInitialized)

    useEffect(() => {
        // React Strict Mode에서 중복 실행 방지
        if (!isInitialized) {
            initialize()
        }
    }, [initialize, isInitialized])

    return children
}
