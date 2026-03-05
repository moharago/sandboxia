"""Eligibility Evaluator 전용 Tools

Rule Screener: 규제 저촉 키워드/조건 탐지
Decision Composer: 최종 판정 통합
"""

import json

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .state import ScreeningResult


# ================================
# Tool 출력 스키마
# ================================
class DecisionOutput(BaseModel):
    """판정 통합 결과"""

    eligibility_label: str = Field(description="판정 결과")
    confidence_score: float = Field(description="신뢰도")
    reasoning: str = Field(description="판정 근거 요약")


# ================================
# 규제 키워드 사전
# ================================
REGULATION_KEYWORDS = {
    "healthcare": [
        "의료", "진료", "진단", "처방", "의사", "간호사", "병원",
        "원격의료", "비대면 진료", "헬스케어", "건강", "의료기기",
        "의약품", "임상", "환자", "치료",
    ],
    "finance": [
        "금융", "결제", "송금", "대출", "투자", "보험", "은행",
        "핀테크", "가상자산", "암호화폐", "P2P", "크라우드펀딩",
        "신용", "여신", "수신",
    ],
    "mobility": [
        "자율주행", "드론", "UAM", "모빌리티", "운송", "배달",
        "퍼스널모빌리티", "킥보드", "전동", "운전", "주행",
        "도로", "항공", "운항",
    ],
    "data": [
        "개인정보", "데이터", "프라이버시", "정보주체", "동의",
        "가명정보", "익명정보", "빅데이터", "AI", "인공지능",
        "알고리즘", "프로파일링",
    ],
    "telecom": [
        "전기통신", "이동통신", "통신사업", "주파수", "전파", "방송", "5G", "6G",
        "IoT", "사물인터넷",
    ],
}

# 고위험 키워드 (규제 저촉 가능성 높음)
HIGH_RISK_KEYWORDS = [
    "원격의료", "비대면 진료", "자율주행", "드론 배송",
    "가상자산", "암호화폐", "P2P 대출", "개인정보 제3자 제공",
    "의료기기", "의약품", "임상시험", "금융상품",
]


@tool
def rule_screener(service_description: str, service_name: str = "") -> ScreeningResult:
    """규제 저촉 가능성 스크리닝

    서비스 설명에서 규제 저촉 키워드와 도메인을 탐지합니다.
    RAG 검색 전 초기 스크리닝 용도로 사용됩니다.

    Args:
        service_description: 서비스 설명 텍스트
        service_name: 서비스명 (선택)

    Returns:
        ScreeningResult: 스크리닝 결과 (리스크 신호, 도메인, 검색 키워드)

    Example:
        >>> rule_screener("AI 기반 비대면 진료 서비스")
        ScreeningResult(has_regulation_risk=True, detected_domains=["healthcare"], ...)
    """
    text = f"{service_name} {service_description}".lower()

    detected_domains: list[str] = []
    risk_signals: list[str] = []
    search_keywords: list[str] = []

    # 도메인별 키워드 탐지
    for domain, keywords in REGULATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                print(f"[DEBUG] rule_screener: 키워드 '{keyword}' 감지 → 도메인 '{domain}'")
                if domain not in detected_domains:
                    detected_domains.append(domain)
                if keyword not in search_keywords:
                    search_keywords.append(keyword)

    # 고위험 키워드 탐지
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in text:
            risk_signals.append(f"고위험 키워드 탐지: {keyword}")

    # 규제 저촉 가능성 판단
    has_regulation_risk = len(risk_signals) > 0 or len(detected_domains) >= 2

    # 신뢰도 계산
    confidence = min(0.5 + len(risk_signals) * 0.1 + len(detected_domains) * 0.1, 0.95)

    return ScreeningResult(
        has_regulation_risk=has_regulation_risk,
        risk_signals=risk_signals,
        detected_domains=detected_domains,
        search_keywords=search_keywords[:10],  # 최대 10개
        confidence=round(confidence, 2),
    )


@tool
def decision_composer(
    screening_result: str,
    regulation_count: int,
    case_count: int,
    has_similar_approved_case: bool,
    has_regulation_conflict: bool,
) -> DecisionOutput:
    """최종 판정 통합

    스크리닝 결과와 RAG 검색 결과를 종합하여 최종 판정을 도출합니다.

    Args:
        screening_result: rule_screener 결과 (JSON 문자열)
        regulation_count: 관련 규제 검색 결과 수
        case_count: 유사 승인 사례 수
        has_similar_approved_case: 유사 승인 사례 존재 여부
        has_regulation_conflict: 규제 저촉 여부

    Returns:
        DecisionOutput: 판정 결과 (label, score, reasoning)

    Example:
        >>> decision_composer(screening_json, 5, 3, True, False)
        DecisionOutput(eligibility_label="not_required", confidence_score=0.85, ...)
    """
    # 스크리닝 결과 파싱
    try:
        screening = json.loads(screening_result)
    except json.JSONDecodeError:
        screening = {"has_regulation_risk": False, "risk_signals": []}

    # 판정 로직
    if has_regulation_conflict:
        # 규제 저촉 → 샌드박스 필요
        label = "required"
        reasoning = "현행 규제에 저촉되는 사항이 확인되어 규제 샌드박스 신청이 필요합니다."
        base_confidence = 0.85

    elif has_similar_approved_case and not screening.get("has_regulation_risk", False):
        # 유사 승인 사례 있고, 리스크 신호 없음 → 출시 가능
        label = "not_required"
        reasoning = "유사한 서비스가 이미 승인된 사례가 있으며, 규제 저촉 사항이 없습니다."
        base_confidence = 0.80

    elif screening.get("has_regulation_risk", False) and regulation_count > 0:
        # 리스크 신호 있고 관련 규제 있음 → 샌드박스 필요
        label = "required"
        reasoning = "규제 저촉 가능성이 탐지되었으며, 관련 규제가 존재합니다."
        base_confidence = 0.75

    elif case_count == 0 and regulation_count == 0:
        # 정보 부족 → 불명확
        label = "unclear"
        reasoning = "관련 사례와 규제 정보가 충분하지 않아 추가 검토가 필요합니다."
        base_confidence = 0.50

    else:
        # 기타 → 불명확
        label = "unclear"
        reasoning = "명확한 판정이 어려워 추가 검토가 필요합니다."
        base_confidence = 0.60

    # 신뢰도 조정 (정보량에 따라)
    info_bonus = min((regulation_count + case_count) * 0.02, 0.1)
    confidence_score = min(base_confidence + info_bonus, 0.95)

    return DecisionOutput(
        eligibility_label=label,
        confidence_score=round(confidence_score, 2),
        reasoning=reasoning,
    )
