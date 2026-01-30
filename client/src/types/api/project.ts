/**
 * Project API Types
 */

export interface CreateProjectRequest {
    user_id: string
    company_name: string
    service_name?: string
    service_description?: string
    industry?: string
}

export interface ProjectResponse {
    id: string
    user_id: string
    company_name: string
    service_name: string | null
    service_description: string | null
    industry: string | null
    additional_notes: string | null
    status: number
    current_step: number
    track: string | null
    canonical: Record<string, unknown>
    application_input: Record<string, unknown>
    application_draft: Record<string, unknown>
    created_at: string
    updated_at: string
}
