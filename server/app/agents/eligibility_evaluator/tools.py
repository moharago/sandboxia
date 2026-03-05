"""Eligibility Evaluator 전용 Tools

Rule Screener: 규제 저촉 키워드/조건 탐지
"""

from langchain_core.tools import tool

from .state import ScreeningResult


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
