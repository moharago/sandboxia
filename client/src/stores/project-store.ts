import type { ProjectStatus } from "@/types/data/project"
import { create } from "zustand"
import { persist } from "zustand/middleware"

interface ProjectStatusOverride {
    status: ProjectStatus
    updatedAt: string
}

interface ProjectState {
    // 프로젝트 상태 오버라이드 (projectId -> status)
    statusOverrides: Record<string, ProjectStatusOverride>

    // 프로젝트 상태 변경
    updateProjectStatus: (projectId: string, status: ProjectStatus) => void

    // 특정 프로젝트의 오버라이드된 상태 가져오기
    getProjectStatus: (projectId: string, originalStatus: ProjectStatus) => ProjectStatus

    // 오버라이드 초기화
    resetProjectStatus: (projectId: string) => void
    resetAllStatuses: () => void
}

export const useProjectStore = create<ProjectState>()(
    persist(
        (set, get) => ({
            statusOverrides: {},

            updateProjectStatus: (projectId, status) =>
                set((state) => ({
                    statusOverrides: {
                        ...state.statusOverrides,
                        [projectId]: {
                            status,
                            updatedAt: new Date().toISOString(),
                        },
                    },
                })),

            getProjectStatus: (projectId, originalStatus) => {
                const override = get().statusOverrides[projectId]
                return override ? override.status : originalStatus
            },

            resetProjectStatus: (projectId) =>
                set((state) => {
                    const { [projectId]: _, ...rest } = state.statusOverrides
                    return { statusOverrides: rest }
                }),

            resetAllStatuses: () => set({ statusOverrides: {} }),
        }),
        {
            name: "sandbox-project-storage",
        }
    )
)
