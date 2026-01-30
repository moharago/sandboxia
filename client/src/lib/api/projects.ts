/**
 * Projects API Client
 *
 * Supabase를 직접 호출하여 프로젝트 생성 처리
 */

import { createClient } from "@/lib/supabase/client"
import type { CreateProjectRequest, ProjectResponse } from "@/types/api/project"

export const projectsApi = {
    /**
     * 새 프로젝트 생성
     */
    createProject: async (request: CreateProjectRequest): Promise<ProjectResponse> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("projects")
            .insert({
                user_id: request.user_id,
                company_name: request.company_name,
                service_name: request.service_name,
                service_description: request.service_description,
                industry: request.industry,
                status: 1,
                current_step: 1,
            })
            .select()
            .single()

        if (error) {
            throw new Error(error.message)
        }

        return data as ProjectResponse
    },
}
