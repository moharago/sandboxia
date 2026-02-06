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

/** 신청서 카드 부분 업데이트 요청 */
export interface DraftCardUpdateRequest {
    project_id: string
    card_key: string
    card_data: Record<string, string>
}

/** 신청서 카드 부분 업데이트 응답 */
export interface DraftCardUpdateResponse {
    success: boolean
    project_id: string
    card_key: string
}
