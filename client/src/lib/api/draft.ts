/**
 * Draft API Client
 *
 * Supabase에서 projects.application_draft 조회
 */

import { createClient } from "@/lib/supabase/client"
import type { ApplicationDraft } from "@/types/api/draft"

export const draftApi = {
    /**
     * 프로젝트의 신청서 초안 데이터 조회
     * 결과가 없으면 null 반환
     */
    getByProjectId: async (projectId: string): Promise<ApplicationDraft | null> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("projects")
            .select("application_draft")
            .eq("id", projectId)
            .single()

        if (error) {
            throw new Error(error.message)
        }

        return (data?.application_draft as ApplicationDraft) ?? null
    },
}
