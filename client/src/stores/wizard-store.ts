import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { ProjectStage } from "@/types/data/project"
import type { Track } from "@/types/data/track"

interface ServiceData {
    companyName: string
    serviceName: string
    description: string
    memo: string
}

type MarketDecision = "direct" | "sandbox"

interface MarketAnalysis {
    decision: MarketDecision
    aiRecommendation: MarketDecision
}

interface DraftData {
    title: string
    summary: string
    sections: Record<string, string>
    lastSaved: string
}

export type FormType = "counseling" | "temporary" | "demonstration" | "fastcheck"

export const FORM_TYPE_LABELS: Record<FormType, string> = {
    counseling: "상담신청",
    temporary: "임시허가",
    demonstration: "실증특례",
    fastcheck: "신속확인",
}

interface WizardState {
    currentStep: ProjectStage
    completedSteps: ProjectStage[]
    serviceData: ServiceData | null
    marketAnalysis: MarketAnalysis | null
    trackSelection: Track | null
    draftData: DraftData | null
    selectedFormType: FormType

    setCurrentStep: (step: ProjectStage) => void
    markStepComplete: (step: ProjectStage) => void
    unmarkStepComplete: (step: ProjectStage) => void
    setServiceData: (data: ServiceData) => void
    setMarketAnalysis: (data: MarketAnalysis) => void
    setTrackSelection: (track: Track | null) => void
    setDraftData: (data: DraftData) => void
    updateDraftSection: (sectionKey: string, content: string) => void
    setSelectedFormType: (formType: FormType) => void
    resetWizard: () => void
}

const initialState = {
    currentStep: 1 as ProjectStage,
    completedSteps: [] as ProjectStage[],
    serviceData: null,
    marketAnalysis: null,
    trackSelection: null,
    draftData: null,
    selectedFormType: "counseling" as FormType,
}

export const useWizardStore = create<WizardState>()(
    persist(
        (set, get) => ({
            ...initialState,

            setCurrentStep: (step) => set({ currentStep: step }),

            markStepComplete: (step) =>
                set((state) => ({
                    completedSteps: state.completedSteps.includes(step)
                        ? state.completedSteps
                        : [...state.completedSteps, step].sort((a, b) => a - b),
                })),

            unmarkStepComplete: (step) =>
                set((state) => ({
                    completedSteps: state.completedSteps.filter((s) => s !== step),
                })),

            setServiceData: (data) => set({ serviceData: data }),

            setMarketAnalysis: (data) => set({ marketAnalysis: data }),

            setTrackSelection: (track) => set({ trackSelection: track }),

            setDraftData: (data) => set({ draftData: data }),

            updateDraftSection: (sectionKey, content) =>
                set((state) => ({
                    draftData: state.draftData
                        ? {
                              ...state.draftData,
                              sections: {
                                  ...state.draftData.sections,
                                  [sectionKey]: content,
                              },
                              lastSaved: new Date().toISOString(),
                          }
                        : null,
                })),

            setSelectedFormType: (formType) => set({ selectedFormType: formType }),

            resetWizard: () => set(initialState),
        }),
        {
            name: "sandbox-wizard-storage",
            partialize: (state) => ({
                currentStep: state.currentStep,
                completedSteps: state.completedSteps,
                serviceData: state.serviceData,
                marketAnalysis: state.marketAnalysis,
                trackSelection: state.trackSelection,
                draftData: state.draftData,
                selectedFormType: state.selectedFormType,
            }),
        }
    )
)
