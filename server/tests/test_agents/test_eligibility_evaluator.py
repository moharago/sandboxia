"""Eligibility Evaluator 에이전트 테스트

테스트 범위:
- 헬퍼 함수 (canonical 필드 추출)
- Tools (rule_screener, decision_composer)
- 노드 함수 (screen_node 등)
"""

import pytest

from app.agents.eligibility_evaluator.nodes import (
    get_service_description,
    get_service_info,
    get_service_name,
)
from app.agents.eligibility_evaluator.schemas import EligibilityLabel
from app.agents.eligibility_evaluator.state import ScreeningResult
from app.agents.eligibility_evaluator.tools import decision_composer, rule_screener


class TestCanonicalHelpers:
    """canonical 헬퍼 함수 테스트"""

    def test_get_service_info_camelcase(self, sample_canonical_camelcase):
        """camelCase 형식 지원 테스트"""
        result = get_service_info(sample_canonical_camelcase)

        assert "serviceName" in result
        assert result["serviceName"] == "AI 건강 상담 서비스"

    def test_get_service_info_snakecase(self, sample_canonical_snakecase):
        """snake_case 형식 지원 테스트"""
        result = get_service_info(sample_canonical_snakecase)

        assert "service_name" in result
        assert result["service_name"] == "AI 기반 도축 자동 검인 서비스"

    def test_get_service_description_camelcase(self, sample_canonical_camelcase):
        """서비스 설명 추출 (camelCase)"""
        result = get_service_description(sample_canonical_camelcase)

        assert "증상을 입력하면" in result

    def test_get_service_description_snakecase(self, sample_canonical_snakecase):
        """서비스 설명 추출 (snake_case - what_action 사용)"""
        result = get_service_description(sample_canonical_snakecase)

        assert "영상 분석 기술" in result

    def test_get_service_name_camelcase(self, sample_canonical_camelcase):
        """서비스명 추출 (camelCase)"""
        result = get_service_name(sample_canonical_camelcase)

        assert result == "AI 건강 상담 서비스"

    def test_get_service_name_snakecase(self, sample_canonical_snakecase):
        """서비스명 추출 (snake_case)"""
        result = get_service_name(sample_canonical_snakecase)

        assert result == "AI 기반 도축 자동 검인 서비스"

    def test_get_service_info_empty(self):
        """빈 canonical 처리"""
        result = get_service_info({})

        assert result == {}

    def test_get_service_description_empty(self):
        """서비스 설명 없는 경우"""
        result = get_service_description({})

        assert result == ""


class TestRuleScreener:
    """rule_screener 도구 테스트"""

    def test_healthcare_domain_detection(self):
        """의료 도메인 키워드 탐지"""
        result = rule_screener.invoke({
            "service_description": "AI 기반 비대면 진료 서비스",
            "service_name": "원격의료 앱",
        })

        assert result.has_regulation_risk is True
        assert "healthcare" in result.detected_domains
        assert any("원격의료" in signal for signal in result.risk_signals)

    def test_finance_domain_detection(self):
        """금융 도메인 키워드 탐지"""
        result = rule_screener.invoke({
            "service_description": "가상자산 거래소 및 암호화폐 투자 플랫폼",
            "service_name": "핀테크 앱",
        })

        assert result.has_regulation_risk is True  # 고위험 키워드: 가상자산, 암호화폐
        assert "finance" in result.detected_domains

    def test_no_risk_service(self):
        """규제 리스크 없는 서비스"""
        result = rule_screener.invoke({
            "service_description": "맛집 추천 앱",
            "service_name": "푸드 가이드",
        })

        assert result.has_regulation_risk is False
        assert len(result.risk_signals) == 0

    def test_multi_domain_detection(self):
        """복수 도메인 탐지"""
        result = rule_screener.invoke({
            "service_description": "AI 기반 건강 데이터 분석 및 금융 보험 추천",
            "service_name": "",
        })

        assert len(result.detected_domains) >= 2
        assert "healthcare" in result.detected_domains or "data" in result.detected_domains

    def test_search_keywords_generated(self):
        """검색 키워드 생성"""
        result = rule_screener.invoke({
            "service_description": "자율주행 드론 배송 서비스",
            "service_name": "드론 딜리버리",
        })

        assert len(result.search_keywords) > 0
        assert "mobility" in result.detected_domains or "드론" in result.search_keywords


class TestDecisionComposer:
    """decision_composer 도구 테스트"""

    def test_regulation_conflict_required(self):
        """규제 저촉 → 샌드박스 필요"""
        result = decision_composer.invoke({
            "screening_result": '{"has_regulation_risk": true, "risk_signals": ["고위험"]}',
            "regulation_count": 5,
            "case_count": 2,
            "has_similar_approved_case": False,
            "has_regulation_conflict": True,
        })

        assert result.eligibility_label == "required"
        assert result.confidence_score >= 0.8

    def test_similar_case_not_required(self):
        """유사 승인 사례 있음 → 출시 가능"""
        result = decision_composer.invoke({
            "screening_result": '{"has_regulation_risk": false, "risk_signals": []}',
            "regulation_count": 0,
            "case_count": 3,
            "has_similar_approved_case": True,
            "has_regulation_conflict": False,
        })

        assert result.eligibility_label == "not_required"
        assert result.confidence_score >= 0.7

    def test_no_info_unclear(self):
        """정보 부족 → 불명확"""
        result = decision_composer.invoke({
            "screening_result": '{"has_regulation_risk": false}',
            "regulation_count": 0,
            "case_count": 0,
            "has_similar_approved_case": False,
            "has_regulation_conflict": False,
        })

        assert result.eligibility_label == "unclear"
        assert result.confidence_score <= 0.6

    def test_invalid_json_fallback(self):
        """잘못된 JSON 처리"""
        result = decision_composer.invoke({
            "screening_result": "invalid json",
            "regulation_count": 0,
            "case_count": 0,
            "has_similar_approved_case": False,
            "has_regulation_conflict": False,
        })

        # 에러 없이 처리되어야 함
        assert result.eligibility_label in ["required", "not_required", "unclear"]


class TestScreeningResult:
    """ScreeningResult 모델 테스트"""

    def test_model_creation(self, sample_screening_result):
        """모델 생성"""
        assert sample_screening_result.has_regulation_risk is True
        assert len(sample_screening_result.detected_domains) == 2

    def test_model_dump(self, sample_screening_result):
        """dict 변환"""
        data = sample_screening_result.model_dump()

        assert "has_regulation_risk" in data
        assert "detected_domains" in data


class TestSimilarityConversion:
    """similarity 값 변환 테스트"""

    def test_distance_to_similarity(self):
        """ChromaDB distance → similarity 변환"""
        # distance = 1.1 → similarity ≈ 48%
        distance = 1.1
        similarity = int(100 / (1 + distance))

        assert 40 <= similarity <= 50

    def test_low_distance_high_similarity(self):
        """낮은 distance = 높은 similarity"""
        distance = 0.5
        similarity = int(100 / (1 + distance))

        assert similarity >= 60

    def test_high_distance_low_similarity(self):
        """높은 distance = 낮은 similarity"""
        distance = 3.0
        similarity = int(100 / (1 + distance))

        assert similarity <= 30


class TestEligibilityLabel:
    """EligibilityLabel enum 테스트"""

    def test_enum_values(self):
        """enum 값 확인"""
        assert EligibilityLabel.REQUIRED.value == "required"
        assert EligibilityLabel.NOT_REQUIRED.value == "not_required"
        assert EligibilityLabel.UNCLEAR.value == "unclear"

    def test_enum_from_string(self):
        """문자열에서 enum 변환"""
        label = EligibilityLabel("required")
        assert label == EligibilityLabel.REQUIRED
