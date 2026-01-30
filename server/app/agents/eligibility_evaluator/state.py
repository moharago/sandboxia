"""Eligibility Evaluator 에이전트 상태 정의

에이전트가 처리하는 데이터 흐름:
입력 (canonical) → 중간 결과 (RAG 검색) → 최종 출력 (판정 결과)
"""

from pydantic import BaseModel, Field

from .schemas import (
    ApprovalCase,
    DirectLaunchRisk,
    EligibilityLabel,
    JudgmentSummary,
    Regulation,
)


class ScreeningResult(BaseModel):
    """규제 스크리닝 결과"""

    has_regulation_risk: bool = Field(default=False, description="규제 저촉 가능성")
    risk_signals: list[str] = Field(default_factory=list, description="리스크 신호")
    detected_domains: list[str] = Field(default_factory=list, description="탐지된 도메인")
    search_keywords: list[str] = Field(default_factory=list, description="검색 키워드")
    confidence: float = Field(default=0.0, description="스크리닝 신뢰도")


class EligibilityState(BaseModel):
    """Eligibility Evaluator 에이전트 상태

    Attributes:
        # 입력
        project_id: 프로젝트 UUID
        canonical: 서비스 정보 통일 구조 (projects.canonical)

        # 중간 결과 (RAG 검색)
        screening_result: Rule Screener 결과
        regulation_results: R1 검색 결과 (규제제도/절차)
        case_results: R2 검색 결과 (승인 사례)
        law_results: R3 검색 결과 (도메인별 법령)

        # 최종 출력 (DB 저장용)
        eligibility_label: 판정 결과 (required/not_required/unclear)
        confidence_score: 신뢰도 (0~1)
        result_summary: AI 분석 결과 요약
        direct_launch_risks: 바로 출시 시 리스크
        judgment_summary: 판단 근거 (왼쪽 패널)
        approval_cases: 승인 사례 (오른쪽 패널 - Step 2,3,4 재사용)
        regulations: 법령·제도 (오른쪽 패널 - Step 2,3,4 재사용)
    """

    # 입력
    project_id: str = Field(description="프로젝트 UUID")
    canonical: dict = Field(default_factory=dict, description="서비스 정보")

    # 중간 결과 (RAG 검색)
    screening_result: ScreeningResult | None = Field(
        default=None, description="스크리닝 결과"
    )
    regulation_results: list[dict] = Field(
        default_factory=list, description="R1 검색 결과"
    )
    case_results: list[dict] = Field(
        default_factory=list, description="R2 검색 결과"
    )
    law_results: list[dict] = Field(
        default_factory=list, description="R3 검색 결과"
    )

    # 최종 출력
    eligibility_label: EligibilityLabel | None = Field(
        default=None, description="판정 결과"
    )
    confidence_score: float | None = Field(
        default=None, description="신뢰도"
    )
    result_summary: str | None = Field(
        default=None, description="결과 요약"
    )
    direct_launch_risks: list[DirectLaunchRisk] = Field(
        default_factory=list, description="바로 출시 시 리스크"
    )
    judgment_summary: list[JudgmentSummary] = Field(
        default_factory=list, description="판단 근거"
    )
    approval_cases: list[ApprovalCase] = Field(
        default_factory=list, description="승인 사례"
    )
    regulations: list[Regulation] = Field(
        default_factory=list, description="법령·제도"
    )

    class Config:
        arbitrary_types_allowed = True
