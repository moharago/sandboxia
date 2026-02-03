"""Eligibility Evaluator 스키마 정의

DB 테이블 eligibility_results와 매핑되는 Pydantic 모델
"""

from enum import Enum

from pydantic import BaseModel, Field


# ================================
# Enum 정의
# ================================
class EligibilityLabel(str, Enum):
    """대상성 판단 결과 라벨"""

    REQUIRED = "required"  # 규제 샌드박스 신청 필요
    NOT_REQUIRED = "not_required"  # 바로 시장 출시 가능
    UNCLEAR = "unclear"  # 불명확 - 추가 검토 필요


class JudgmentType(str, Enum):
    """판단 근거 유형"""

    LAW = "법령 기준"
    CASE = "사례 기준"
    REGULATION = "규제 기준"


class ReasonType(str, Enum):
    """리스크/사유 유형"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# ================================
# evidence_data 내부 구조
# ================================
class JudgmentSummary(BaseModel):
    """Step 2 판단 근거 (왼쪽 패널)"""

    type: JudgmentType = Field(description="근거 유형 (법령/사례/규제 기준)")
    title: str = Field(description="근거 제목")
    summary: str = Field(description="설명 텍스트")
    source: str = Field(description="근거 출처")


class ApprovalCase(BaseModel):
    """승인 사례 (오른쪽 패널 - 승인사례 탭)

    Step 2, 3, 4에서 재사용
    """

    track: str = Field(description="트랙 (실증특례/임시허가)")
    date: str = Field(description="승인 날짜")
    similarity: int = Field(description="유사도 (%)")
    title: str = Field(description="사례 제목")
    company: str = Field(description="회사명")
    summary: str = Field(description="요약")
    detail_url: str | None = Field(default=None, description="상세보기 링크")


class Regulation(BaseModel):
    """법령·제도 (오른쪽 패널 - 법령·제도 탭)

    Step 2, 3, 4에서 재사용
    """

    category: str = Field(description="카테고리 (실증특례/임시허가/절차/참고)")
    title: str = Field(description="법령명")
    summary: str = Field(description="요약")
    source_url: str | None = Field(default=None, description="원문보기 링크")


class EvidenceData(BaseModel):
    """판단 근거 통합 구조 (evidence_data JSONB)"""

    judgment_summary: list[JudgmentSummary] = Field(
        default_factory=list,
        description="Step 2 판단 근거 (왼쪽)",
    )
    approval_cases: list[ApprovalCase] = Field(
        default_factory=list,
        description="승인사례 탭 (오른쪽) - Step 2,3,4 재사용",
    )
    regulations: list[Regulation] = Field(
        default_factory=list,
        description="법령·제도 탭 (오른쪽) - Step 2,3,4 재사용",
    )


# ================================
# 바로 출시 시 리스크
# ================================
class DirectLaunchRisk(BaseModel):
    """바로 시장 출시 시 리스크"""

    type: ReasonType = Field(description="리스크 유형")
    title: str = Field(description="리스크 제목")
    description: str = Field(description="리스크 설명")
    source: str | None = Field(default=None, description="근거 출처")


# ================================
# 최종 결과 (API 응답 & DB 저장)
# ================================
class EligibilityResult(BaseModel):
    """대상성 판단 결과 (eligibility_results 테이블)"""

    eligibility_label: EligibilityLabel = Field(
        description="판정 결과 (required/not_required/unclear)"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="신뢰도 (0~1)",
    )
    result_summary: str = Field(description="AI 분석 결과 요약 텍스트")
    direct_launch_risks: list[DirectLaunchRisk] = Field(
        default_factory=list,
        description="바로 출시 시 리스크",
    )
    evidence_data: EvidenceData = Field(
        default_factory=EvidenceData,
        description="판단 근거 + 승인사례 + 법령",
    )
    model_name: str = Field(
        default="",
        description="사용된 LLM 모델명",
    )


# ================================
# API 요청/응답
# ================================
class EligibilityRequest(BaseModel):
    """대상성 판단 API 요청"""

    project_id: str = Field(description="프로젝트 UUID")


class EligibilityResponse(EligibilityResult):
    """대상성 판단 API 응답

    EligibilityResult를 상속하여 동일한 구조 사용
    """

    pass
