import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CaseStage, Track } from '@/types/data';

interface ServiceData {
  companyName: string;
  serviceName: string;
  description: string;
  technology: string;
  targetMarket: string;
}

interface MarketData {
  marketSize: string;
  competitors: string[];
  differentiators: string[];
  targetCustomers: string;
}

interface DraftData {
  title: string;
  summary: string;
  sections: Record<string, string>;
  lastSaved: string;
}

interface WizardState {
  currentStep: CaseStage;
  completedSteps: CaseStage[];
  serviceData: ServiceData | null;
  marketData: MarketData | null;
  trackSelection: Track | null;
  draftData: DraftData | null;

  setCurrentStep: (step: CaseStage) => void;
  markStepComplete: (step: CaseStage) => void;
  unmarkStepComplete: (step: CaseStage) => void;
  setServiceData: (data: ServiceData) => void;
  setMarketData: (data: MarketData) => void;
  setTrackSelection: (track: Track | null) => void;
  setDraftData: (data: DraftData) => void;
  updateDraftSection: (sectionKey: string, content: string) => void;
  resetWizard: () => void;
}

const initialState = {
  currentStep: 1 as CaseStage,
  completedSteps: [] as CaseStage[],
  serviceData: null,
  marketData: null,
  trackSelection: null,
  draftData: null,
};

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

      setServiceData: (data) =>
        set({ serviceData: data }),

      setMarketData: (data) =>
        set({ marketData: data }),

      setTrackSelection: (track) =>
        set({ trackSelection: track }),

      setDraftData: (data) =>
        set({ draftData: data }),

      updateDraftSection: (sectionKey, content) =>
        set((state) => ({
          draftData: state.draftData
            ? {
                ...state.draftData,
                sections: { ...state.draftData.sections, [sectionKey]: content },
                lastSaved: new Date().toISOString(),
              }
            : null,
        })),

      resetWizard: () => set(initialState),
    }),
    {
      name: 'sandbox-wizard-storage',
      partialize: (state) => ({
        currentStep: state.currentStep,
        completedSteps: state.completedSteps,
        serviceData: state.serviceData,
        marketData: state.marketData,
        trackSelection: state.trackSelection,
        draftData: state.draftData,
      }),
    }
  )
);
