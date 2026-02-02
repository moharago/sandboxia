/**
 * Eligibility Evaluator API Types
 *
 * 대상성 판단 API 요청/응답 타입
 */

// Enum 타입
export type EligibilityLabel = "required" | "not_required" | "unclear"
export type JudgmentType = "법령 기준" | "사례 기준" | "규제 기준"
export type ReasonType = "positive" | "negative" | "neutral"

// 판단 근거 (왼쪽 패널)
export interface JudgmentSummary {
    type: JudgmentType
    title: string
    summary: string
    source: string
}

// 승인 사례 (오른쪽 패널 - 승인사례 탭)
export interface ApprovalCase {
    track: string
    date: string
    similarity: number
    title: string
    company: string
    summary: string
    detail_url: string | null
}

// 법령/제도 (오른쪽 패널 - 법령/제도 탭)
export interface Regulation {
    category: string
    title: string
    summary: string
    source_url: string | null
}

// 근거 데이터 통합 구조
export interface EvidenceData {
    judgment_summary: JudgmentSummary[]
    approval_cases: ApprovalCase[]
    regulations: Regulation[]
}

// 바로 출시 시 리스크
export interface DirectLaunchRisk {
    type: ReasonType
    title: string
    description: string
    source: string | null
}

// API 요청
export interface EligibilityRequest {
    project_id: string
}

// API 응답
export interface EligibilityResponse {
    eligibility_label: EligibilityLabel
    confidence_score: number
    result_summary: string
    direct_launch_risks: DirectLaunchRisk[]
    evidence_data: EvidenceData
}

// 사용자 최종 선택 타입 (unclear 제외)
export type FinalEligibilityLabel = "required" | "not_required"

// DB 레코드 타입 (Supabase eligibility_results 테이블)
export interface EligibilityResult {
    id: string
    project_id: string
    eligibility_label: EligibilityLabel
    final_eligibility_label: FinalEligibilityLabel | null // 사용자 최종 선택
    confidence_score: number
    result_summary: string
    direct_launch_risks: DirectLaunchRisk[]
    evidence_data: EvidenceData
    created_at: string
}
