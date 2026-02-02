"""Track Recommender Agent 상태 정의"""

from typing import TypedDict


class TrackScore(TypedDict):
    """트랙별 점수"""
    fit_score: int  # 0-100
    rank: int  # 1, 2, 3
    status: str  # "AI 추천" | "조건부 가능" | "비추천"
    criteria_results: list[dict]  # LLM 체크리스트 결과


class TrackReason(TypedDict):
    """트랙 추천 이유"""
    type: str  # "positive" | "negative" | "neutral"
    text: str


class TrackEvidence(TypedDict):
    """트랙 추천 근거"""
    source_type: str  # "법령" | "사례" | "규제"
    source: str


class TrackComparison(TypedDict):
    """트랙별 비교 데이터"""
    fit_score: int
    rank: int
    status: str
    reasons: list[TrackReason]
    evidence: list[TrackEvidence]


class TrackRecommenderState(TypedDict):
    """Track Recommender Agent 상태"""

    # 입력
    project_id: str
    canonical: dict  # projects.canonical
    eligibility_result: dict | None  # eligibility_results 테이블

    # 중간 결과
    track_scores: dict[str, TrackScore]  # {demo, temp_permit, quick_check}
    track_definitions: list[dict]  # R1 RAG 결과
    similar_cases: dict[str, list[dict]]  # 트랙별 R2 RAG 결과

    # 최종 출력
    recommended_track: str  # "demo" | "temp_permit" | "quick_check"
    confidence_score: float  # 0-100
    result_summary: str  # AI 분석 요약
    track_comparison: dict[str, TrackComparison]  # JSONB 구조
