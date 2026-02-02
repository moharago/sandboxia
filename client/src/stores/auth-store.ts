import { createClient } from "@/lib/supabase/client"
import type { User as SupabaseUser } from "@supabase/supabase-js"
import { create } from "zustand"

export interface UserProfile {
    id: string
    email: string
    name: string | null
    company: string | null
    phone: string | null
    status: "PENDING" | "ACTIVE"
    created_at: string
}

interface AuthState {
    user: SupabaseUser | null
    profile: UserProfile | null
    isLoading: boolean
    isInitialized: boolean

    initialize: () => Promise<void>
    fetchProfile: () => Promise<void>
    updateProfile: (data: Partial<Pick<UserProfile, "name" | "company" | "phone" | "status">>) => Promise<void>
    signOut: () => Promise<void>
    reset: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
    user: null,
    profile: null,
    isLoading: false,
    isInitialized: false,

    initialize: async () => {
        const supabase = createClient()

        // 현재 세션 확인
        const {
            data: { session },
        } = await supabase.auth.getSession()

        if (session?.user) {
            set({ user: session.user })
            await get().fetchProfile()
        }

        set({ isInitialized: true })

        // 인증 상태 변경 구독
        supabase.auth.onAuthStateChange(async (event, session) => {
            if (event === "SIGNED_IN" && session?.user) {
                set({ user: session.user })
                await get().fetchProfile()
            } else if (event === "SIGNED_OUT") {
                get().reset()
            }
        })
    },

    fetchProfile: async () => {
        const { user } = get()
        if (!user) return

        set({ isLoading: true })

        try {
            const supabase = createClient()
            const { data, error } = await supabase.from("users").select("*").eq("id", user.id).single()

            if (error) throw error

            set({ profile: data as UserProfile })
        } catch (error) {
            console.error("Failed to fetch profile:", error)
        } finally {
            set({ isLoading: false })
        }
    },

    updateProfile: async (data) => {
        const { user } = get()
        if (!user) return

        set({ isLoading: true })

        try {
            const supabase = createClient()
            const { data: updated, error } = await supabase
                .from("users")
                .update(data)
                .eq("id", user.id)
                .select()
                .single()

            if (error) throw error

            set({ profile: updated as UserProfile })
        } catch (error) {
            console.error("Failed to update profile:", error)
            throw error
        } finally {
            set({ isLoading: false })
        }
    },

    signOut: async () => {
        const supabase = createClient()
        await supabase.auth.signOut()
        get().reset()
    },

    reset: () => {
        set({
            user: null,
            profile: null,
            isLoading: false,
        })
    },
}))
