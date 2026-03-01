import type { NodeInfo } from "@/types/api/agent-progress"
import { create } from "zustand"
import { persist } from "zustand/middleware"

type ViewMode = "grid" | "list"

// 전역 AI 로더 상태
interface GlobalAILoaderState {
    isVisible: boolean
    message?: string
    nodes?: NodeInfo[]
    completedNodes?: string[]
    currentNodeId?: string | null
    progress?: number
}

interface UIState {
    sidebarOpen: boolean
    viewMode: ViewMode
    activeModal: string | null

    // Dev mode
    devMode: boolean
    isAuthenticated: boolean
    devIsAnalyzed: boolean
    devHasChanges: boolean
    devShowAILoader: boolean

    // 전역 AI 로더
    globalAILoader: GlobalAILoaderState

    toggleSidebar: () => void
    setSidebarOpen: (open: boolean) => void
    setViewMode: (mode: ViewMode) => void
    openModal: (modalId: string) => void
    closeModal: () => void
    toggleDevMode: () => void
    setAuthenticated: (auth: boolean) => void
    setDevIsAnalyzed: (value: boolean) => void
    setDevHasChanges: (value: boolean) => void
    setDevShowAILoader: (value: boolean) => void

    // 전역 AI 로더 액션
    showGlobalAILoader: (config: Omit<GlobalAILoaderState, "isVisible">) => void
    updateGlobalAILoader: (config: Partial<Omit<GlobalAILoaderState, "isVisible">>) => void
    hideGlobalAILoader: () => void

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
            devMode: false,
            isAuthenticated: false,
            devIsAnalyzed: false,
            devHasChanges: false,
            devShowAILoader: false,

            // 전역 AI 로더 초기 상태
            globalAILoader: {
                isVisible: false,
            },

            toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
            setSidebarOpen: (open) => set({ sidebarOpen: open }),
            setViewMode: (mode) => set({ viewMode: mode }),
            openModal: (modalId) => set({ activeModal: modalId }),
            closeModal: () => set({ activeModal: null }),
            toggleDevMode: () => set((state) => ({ devMode: !state.devMode })),
            setAuthenticated: (auth) => set({ isAuthenticated: auth }),
            setDevIsAnalyzed: (value) => set({ devIsAnalyzed: value }),
            setDevHasChanges: (value) => set({ devHasChanges: value }),
            setDevShowAILoader: (value) => set({ devShowAILoader: value }),

            // 전역 AI 로더 액션
            showGlobalAILoader: (config) =>
                set({
                    globalAILoader: {
                        isVisible: true,
                        ...config,
                    },
                }),
            updateGlobalAILoader: (config) =>
                set((state) => ({
                    globalAILoader: {
                        ...state.globalAILoader,
                        ...config,
                    },
                })),
            hideGlobalAILoader: () =>
                set({
                    globalAILoader: {
                        isVisible: false,
                    },
                }),

            isNewCaseModalOpen: false,
            openNewCaseModal: () => set({ isNewCaseModalOpen: true }),
            closeNewCaseModal: () => set({ isNewCaseModalOpen: false }),
        }),
        {
            name: "sandbox-ui-storage",
            partialize: (state) => ({
                viewMode: state.viewMode,
            }),
        }
    )
)
