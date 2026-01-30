"use client"

import { useAuthStore } from "@/stores/auth-store"
import type { ReactNode } from "react"
import { useEffect } from "react"

interface AuthProviderProps {
    children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
    const initialize = useAuthStore((state) => state.initialize)

    useEffect(() => {
        initialize()
    }, [initialize])

    return children
}
