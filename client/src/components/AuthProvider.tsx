"use client"

import { useAuthStore } from "@/stores/auth-store"
import type { ReactNode } from "react"
import { useEffect, useRef } from "react"

interface AuthProviderProps {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const initialize = useAuthStore((state) => state.initialize)

    // advanced-init-once: ref로 중복 호출 방지 (비동기 initialize의 Strict Mode 경쟁 조건 해결)
    const initCalledRef = useRef(false)

    useEffect(() => {
        if (initCalledRef.current) return
        initCalledRef.current = true
        initialize()
    }, [initialize])

    return children
}
