/**
 * Project API Types
 */

import type { Project, ProjectStatus, ProjectStep, Track } from "@/types/data/project"

export interface CreateProjectRequest {
    company_name: string
    service_name?: string
    service_description?: string
    industry?: string
}

// DB 응답 타입 (Project와 동일하지만 추가 필드 포함)
export interface ProjectResponse extends Project {
    additional_notes: string | null
    canonical: Record<string, unknown>
    application_input: Record<string, unknown>
    application_draft: Record<string, unknown>
}

// Project 타입으로 변환 (추가 필드 제외)
export const toProject = (response: ProjectResponse): Project => ({
    id: response.id,
    user_id: response.user_id,
    company_name: response.company_name,
    service_name: response.service_name,
    service_description: response.service_description,
    industry: response.industry,
    additional_notes: response.additional_notes,
    status: response.status as ProjectStatus,
    current_step: response.current_step as ProjectStep,
    track: response.track as Track | null,
    created_at: response.created_at,
    updated_at: response.updated_at,
})
