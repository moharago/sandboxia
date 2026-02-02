/**
 * Projects API Client
 *
 * Supabase를 직접 호출하여 프로젝트 CRUD 처리
 */

import { createClient } from "@/lib/supabase/client"
import type { CreateProjectRequest, ProjectResponse } from "@/types/api/project"

export const projectsApi = {
    /**
     * 단일 프로젝트 조회 (RLS 적용)
     */
    getProject: async (id: string): Promise<ProjectResponse> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("projects")
            .select("*")
            .eq("id", id)
            .single()

        if (error) {
            throw new Error(error.message)
        }

        return data as ProjectResponse
    },

    /**
     * 내 프로젝트 목록 조회 (RLS 적용으로 user_id 자동 필터링)
     */
    getMyProjects: async (): Promise<ProjectResponse[]> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("projects")
            .select("*")
            .order("updated_at", { ascending: false })

        if (error) {
            throw new Error(error.message)
        }

        return data as ProjectResponse[]
    },

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
