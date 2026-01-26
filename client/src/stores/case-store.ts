import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CaseStatus } from "@/types/data/case";

interface CaseStatusOverride {
    status: CaseStatus;
    updatedAt: string;
}

interface CaseState {
    // 케이스 상태 오버라이드 (caseId -> status)
    statusOverrides: Record<string, CaseStatusOverride>;

    // 케이스 상태 변경
    updateCaseStatus: (caseId: string, status: CaseStatus) => void;

    // 특정 케이스의 오버라이드된 상태 가져오기
    getCaseStatus: (caseId: string, originalStatus: CaseStatus) => CaseStatus;

    // 오버라이드 초기화
    resetCaseStatus: (caseId: string) => void;
    resetAllStatuses: () => void;
}

export const useCaseStore = create<CaseState>()(
    persist(
        (set, get) => ({
            statusOverrides: {},

            updateCaseStatus: (caseId, status) =>
                set((state) => ({
                    statusOverrides: {
                        ...state.statusOverrides,
                        [caseId]: {
                            status,
                            updatedAt: new Date().toISOString(),
                        },
                    },
                })),

            getCaseStatus: (caseId, originalStatus) => {
                const override = get().statusOverrides[caseId];
                return override ? override.status : originalStatus;
            },

            resetCaseStatus: (caseId) =>
                set((state) => {
                    const { [caseId]: _, ...rest } = state.statusOverrides;
                    return { statusOverrides: rest };
                }),

            resetAllStatuses: () => set({ statusOverrides: {} }),
        }),
        {
            name: "sandbox-case-storage",
        }
    )
);
