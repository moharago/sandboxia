/**
 * Track Recommender API Types
 */

import type { Track } from "@/types/data/project"

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
