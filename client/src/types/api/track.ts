/**
 * Track Recommender API Types
 */

import type { Track } from "@/types/data/project"
import type { ApprovalCase, Regulation } from "./eligibility"

// 트랙 추천 대상 (counseling 제외)
export type RecommendableTrack = Exclude<Track, "counseling">

// 추천 사유 타입
export type ReasonType = "positive" | "negative" | "neutral"

// 트랙 상태
export type TrackStatus = "AI 추천" | "조건부 가능" | "비추천"

// 추천 사유
export interface TrackReason {
    type: ReasonType
    text: string
}

// 근거 정보
export interface TrackEvidence {
    source_type: "사례" | "법령" | "규제"
    source: string
    description?: string
    service_name?: string
    company_name?: string
    track?: string
    source_url?: string
    similarity?: number
}

// 개별 트랙 비교 데이터
export interface TrackComparisonItem {
    fit_score: number
    rank: number
    status: TrackStatus
    reasons: TrackReason[]
    evidence: TrackEvidence[]
}

// 트랙 비교 전체 (3개 트랙)
export type TrackComparison = Record<RecommendableTrack, TrackComparisonItem>

// 유사 승인 사례
export interface SimilarCase {
    case_id: string
    case_name?: string  // case_id에서 추출한 사례명 (컨소시엄명 등)
    company_name: string
    service_name: string
    track: string
    service_description?: string
    special_provisions?: string
    relevance_score?: number
    source_url?: string
}

// 트랙별 유사 사례 목록
export type SimilarCases = Partial<Record<RecommendableTrack, SimilarCase[]>>

// R3 도메인 법령 개별 항목
export interface DomainConstraint {
    content: string           // 조문 내용
    source: string            // 인용 (예: "의료법 제34조 제1항")
    law_name: string          // 법령명
    article_title: string     // 조문 제목
    domain_label: string      // 도메인 한글명
    source_url: string | null // 국가법령정보센터 URL
}

// R3 도메인 법령 RAG 검색 결과
export interface DomainConstraints {
    constraints: DomainConstraint[]
    blocking_regulations: DomainConstraint[]
    has_blocking_issue: boolean
}

// 트랙 추천 요청
export interface TrackRecommendRequest {
    project_id: string
}

// 트랙 추천 응답
export interface TrackRecommendResponse {
    project_id: string
    recommended_track: RecommendableTrack
    confidence_score: number
    result_summary: string
    track_comparison: TrackComparison
    similar_cases?: SimilarCases  // 트랙별 유사 승인 사례 (서버에서 omit 가능)
    domain_constraints?: DomainConstraints  // R3 도메인 법령 RAG 검색 결과
    // ReferencePanel 데이터 (Eligibility Evaluator와 동일 형식)
    approval_cases?: ApprovalCase[]
    regulations?: Regulation[]
}

// 트랙 선택 저장 요청
export interface TrackSelectRequest {
    project_id: string
    track: RecommendableTrack
}

// API 에러 응답
export interface TrackApiError {
    detail: string
}
