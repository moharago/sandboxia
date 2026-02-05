/**
 * Application Drafter (Step 4) 관련 타입
 */

/** 신청서 초안 생성 요청 */
export interface DraftGenerateRequest {
    project_id: string
}

/** 신청서 초안 생성 응답 */
export interface DraftGenerateResponse {
    project_id: string
    track: string
    application_draft: Record<string, unknown>
    model_name: string
}

/** projects.application_draft에 저장되는 구조 */
export interface ApplicationDraft {
    form_values: Record<string, unknown>
    model_name: string
    generated_at: string
}
