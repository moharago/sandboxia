/**
 * Service Structurer API Types
 */

// 컨설턴트 입력 정보
export interface ConsultantInput {
    company_name: string
    service_name: string
    service_description: string
    additional_memo: string
}

// 파싱된 섹션 정보
export interface ParsedSection {
    title: string
    content_preview: string
    fields: Record<string, string>
}

// 파싱된 문서 정보
export interface ParsedDocument {
    file_index: number
    original_filename: string
    assigned_subtype: string | null
    detected_type: string
    detected_subtype: string
    sections: ParsedSection[]
    fields: Record<string, string>
    metadata: Record<string, unknown>
}

// 서비스 파싱 요청 (FormData로 전송)
export interface ServiceParseRequest {
    sessionId: string
    /** 트랙 (counseling/quick_check/temp_permit/demo) */
    requestedTrack: string
    consultantInput: ConsultantInput
    files: File[]
}

// 서비스 파싱 응답
export interface ServiceParseResponse {
    session_id: string
    requested_track: string
    consultant_input: ConsultantInput
    parsed_documents: ParsedDocument[]
}

// API 에러 응답
export interface ServiceApiError {
    detail: string
}
