import { create } from "zustand"
import { persist } from "zustand/middleware"

type ViewMode = "grid" | "list"

interface UIState {
    sidebarOpen: boolean
    viewMode: ViewMode
    activeModal: string | null

    // Dev mode
    devMode: boolean
    isAuthenticated: boolean

    toggleSidebar: () => void
    setSidebarOpen: (open: boolean) => void
    setViewMode: (mode: ViewMode) => void
    openModal: (modalId: string) => void
    closeModal: () => void
    toggleDevMode: () => void
    setAuthenticated: (auth: boolean) => void

    isNewCaseModalOpen: boolean
    openNewCaseModal: () => void
    closeNewCaseModal: () => void
}

export const useUIStore = create<UIState>()(
    persist(
        (set) => ({
            sidebarOpen: false,
            viewMode: "grid",
            activeModal: null,
            devMode: true,
            isAuthenticated: false,

            toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
            setSidebarOpen: (open) => set({ sidebarOpen: open }),
            setViewMode: (mode) => set({ viewMode: mode }),
            openModal: (modalId) => set({ activeModal: modalId }),
            closeModal: () => set({ activeModal: null }),
            toggleDevMode: () => set((state) => ({ devMode: !state.devMode })),
            setAuthenticated: (auth) => set({ isAuthenticated: auth }),

            isNewCaseModalOpen: false,
            openNewCaseModal: () => set({ isNewCaseModalOpen: true }),
            closeNewCaseModal: () => set({ isNewCaseModalOpen: false }),
        }),
        {
            name: "sandbox-ui-storage",
            partialize: (state) => ({
                devMode: state.devMode,
                isAuthenticated: state.isAuthenticated,
                viewMode: state.viewMode,
            }),
        }
    )
)
