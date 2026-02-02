/**
 * Eligibility API Client
 *
 * Supabase에서 eligibility_results 조회
 */

import { createClient } from "@/lib/supabase/client"
import type { EligibilityResult } from "@/types/api/eligibility"

export const eligibilityApi = {
    /**
     * 프로젝트의 eligibility 결과 조회
     * 결과가 없으면 null 반환
     */
    getByProjectId: async (projectId: string): Promise<EligibilityResult | null> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("eligibility_results")
            .select("*")
            .eq("project_id", projectId)
            .maybeSingle()

        if (error) {
            throw new Error(error.message)
        }

        return data as EligibilityResult | null
    },

    /**
     * 기존 결과가 있는지 확인 (evidence_data 유무)
     */
    hasExistingResult: async (projectId: string): Promise<boolean> => {
        const result = await eligibilityApi.getByProjectId(projectId)

        if (!result || !result.evidence_data) {
            return false
        }

        // evidence_data가 빈 객체인지 확인
        return Object.keys(result.evidence_data).length > 0
    },

    /**
     * 사용자 최종 선택 저장
     * @param projectId 프로젝트 ID
     * @param finalLabel 사용자 선택 (required=샌드박스, not_required=바로출시)
     */
    updateFinalDecision: async (
        projectId: string,
        finalLabel: "required" | "not_required"
    ): Promise<void> => {
        const supabase = createClient()

        const { error } = await supabase
            .from("eligibility_results")
            .update({ final_eligibility_label: finalLabel })
            .eq("project_id", projectId)

        if (error) {
            throw new Error(error.message)
        }
    },
}
