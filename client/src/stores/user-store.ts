import { create } from "zustand"

interface UserInfo {
    email: string
    name: string | null
    company: string | null
    phone: string | null
}

interface UserState {
    user: UserInfo | null
    setUser: (user: UserInfo | null) => void
    updateUser: (updates: Partial<UserInfo>) => void
}

export const useUserStore = create<UserState>()((set) => ({
    user: null,
    setUser: (user) => set({ user }),
    updateUser: (updates) => set((state) => ({
        user: state.user ? { ...state.user, ...updates } : null
    })),
}))
