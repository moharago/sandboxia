"""pytest 공통 설정 및 fixtures"""

import pytest


# pytest-asyncio 설정
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def sample_canonical_camelcase():
    """camelCase 형식의 canonical 데이터"""
    return {
        "serviceInfo": {
            "serviceName": "AI 건강 상담 서비스",
            "serviceDescription": "사용자가 증상을 입력하면 AI가 분석하여 예상 질환과 권장 진료과를 안내하는 서비스입니다.",
            "targetUsers": "건강 정보가 필요한 일반 사용자",
        },
        "companyInfo": {
            "companyName": "헬스AI",
            "businessNumber": "234-56-78901",
        },
    }


@pytest.fixture
def sample_canonical_snakecase():
    """snake_case 형식의 canonical 데이터"""
    return {
        "service": {
            "service_name": "AI 기반 도축 자동 검인 서비스",
            "what_action": "AI 기반 영상 분석 기술과 로봇 시스템을 결합하여 도축 공정에서 도체 검인 업무를 보조",
            "target_users": "1차: 검사관(B2B) / 2차: 축산물 도축업체",
        },
        "company": {
            "company_name": "㈜로보스",
            "business_number": "1223-45-67890",
        },
        "regulatory": {
            "regulatory_issues": [
                {
                    "summary": "AI 시스템을 활용한 검인 보조 방식의 법적 해석 필요",
                    "status": "unclear",
                }
            ]
        },
    }


@pytest.fixture
def sample_screening_result():
    """스크리닝 결과 샘플"""
    from app.agents.eligibility_evaluator.state import ScreeningResult

    return ScreeningResult(
        has_regulation_risk=True,
        risk_signals=["고위험 키워드 탐지: 원격의료"],
        detected_domains=["healthcare", "data"],
        search_keywords=["의료", "건강", "AI", "진단"],
        confidence=0.75,
    )


@pytest.fixture
def sample_case_results():
    """RAG 검색 결과 (사례) 샘플"""
    return [
        {
            "case_id": "실증특례_100_에이아이포펫",
            "company_name": "㈜에이아이포펫",
            "service_name": "AI를 활용한 수의사의 반려동물 건강상태 모니터링 서비스",
            "track": "실증특례",
            "service_description": "AI기반 소프트웨어(App)를 활용하여 반려동물의 건강상태를 수의사가 비대면으로 모니터링",
            "relevance_score": 1.1,  # ChromaDB distance
        },
        {
            "case_id": "실증특례_79_아이싸이랩",
            "company_name": "아이싸이랩",
            "service_name": "비문인식 기반 반려동물 등록 서비스",
            "track": "실증특례",
            "service_description": "모바일 앱으로 반려동물의 비문(Nose Print)을 촬영하여 등록",
            "relevance_score": 1.15,
        },
    ]


@pytest.fixture
def sample_law_results():
    """RAG 검색 결과 (법령) 샘플"""
    return [
        {
            "law_name": "의료법",
            "article_no": "제17조",
            "article_title": "진단서 등",
            "content": "의료업에 종사하고 직접 진찰하거나 검안한 의사가 아니면 진단서를 작성할 수 없다",
            "citation": "의료법 17",
            "domain": "healthcare",
            "relevance_score": 0.85,
        },
    ]
