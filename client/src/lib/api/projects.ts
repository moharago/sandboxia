/**
 * Projects API Client
 *
 * Supabase를 직접 호출하여 프로젝트 CRUD 처리
 */

import { createClient } from "@/lib/supabase/client"
import type { CreateProjectRequest, ProjectResponse } from "@/types/api/project"
import type { RecommendableTrack } from "@/types/api/track"

export interface ProjectFile {
    id: string
    project_id: string
    file_name: string
    storage_bucket: string
    storage_path: string
    file_type: string | null
    extracted_text: string | null
    created_at: string
}

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
     * user_id는 인증된 세션에서 자동으로 가져옴 (클라이언트 스푸핑 방지)
     */
    createProject: async (request: CreateProjectRequest): Promise<ProjectResponse> => {
        const supabase = createClient()

        // 인증된 사용자 정보 가져오기
        const {
            data: { user },
            error: authError,
        } = await supabase.auth.getUser()

        if (authError || !user) {
            throw new Error("인증이 필요합니다. 로그인 후 다시 시도해주세요.")
        }

        const { data, error } = await supabase
            .from("projects")
            .insert({
                user_id: user.id,
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

    /**
     * 프로젝트 삭제 (RLS 적용)
     */
    deleteProject: async (id: string): Promise<void> => {
        const supabase = createClient()

        const { error } = await supabase
            .from("projects")
            .delete()
            .eq("id", id)

        if (error) {
            throw new Error(error.message)
        }
    },

    /**
     * 프로젝트 status 업데이트 (current_step도 함께 업데이트 가능)
     */
    updateStatus: async (projectId: string, status: number, currentStep?: number): Promise<void> => {
        const supabase = createClient()

        const updateData: { status: number; current_step?: number } = { status }
        if (currentStep !== undefined) {
            updateData.current_step = currentStep
        }

        const { error } = await supabase
            .from("projects")
            .update(updateData)
            .eq("id", projectId)

        if (error) {
            throw new Error(error.message)
        }
    },

    /**
     * 프로젝트 파일 목록 조회
     */
    getProjectFiles: async (projectId: string): Promise<ProjectFile[]> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("project_files")
            .select("*")
            .eq("project_id", projectId)
            .order("created_at", { ascending: true })

        if (error) {
            throw new Error(error.message)
        }

        return data as ProjectFile[]
    },

    /**
     * 프로젝트 파일 다운로드 URL 생성 (서버 API 사용)
     */
    getFileDownloadUrl: async (file: ProjectFile): Promise<string> => {
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
        const response = await fetch(`${apiUrl}/api/v1/files/download/${file.id}`)

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || "다운로드 URL 생성 실패")
        }

        const data = await response.json()
        return data.download_url
    },

    /**
     * 프로젝트 트랙 업데이트 (사용자 최종 선택)
     */
    updateProjectTrack: async (
        projectId: string,
        track: RecommendableTrack
    ): Promise<ProjectResponse> => {
        const supabase = createClient()

        const { data, error } = await supabase
            .from("projects")
            .update({
                track,
                current_step: 4, // Step 4로 진행
                updated_at: new Date().toISOString(),
            })
            .eq("id", projectId)
            .select()
            .single()

        if (error) {
            throw new Error(error.message)
        }

        return data as ProjectResponse
    },
}
