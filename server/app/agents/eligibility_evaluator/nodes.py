"""Eligibility Evaluator 노드 함수

그래프의 각 단계 로직을 정의합니다.
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.tools.shared.rag.case_rag import search_case
from app.tools.shared.rag.domain_law_rag import search_domain_law
from app.tools.shared.rag.regulation_rag import search_regulation

from .prompts import COMPOSE_DECISION_PROMPT, SYSTEM_PROMPT
from .schemas import (
    ApprovalCase,
    DirectLaunchRisk,
    EligibilityLabel,
    JudgmentSummary,
    JudgmentType,
    ReasonType,
    Regulation,
)
from .state import EligibilityState, ScreeningResult
from .tools import decision_composer, rule_screener

logger = logging.getLogger(__name__)


# ================================
# canonical 헬퍼 함수
# ================================
def get_service_info(canonical: dict) -> dict:
    """canonical에서 서비스 정보 추출 (여러 형식 지원)

    지원 형식:
    - {"serviceInfo": {...}} (camelCase)
    - {"service": {...}} (snake_case)
    - 직접 필드 (service_name, service_description 등)
    """
    # camelCase 형식
    if "serviceInfo" in canonical:
        return canonical["serviceInfo"]
    # snake_case 형식
    if "service" in canonical:
        return canonical["service"]
    # 직접 필드가 있는 경우 그대로 반환
    return canonical


def get_service_description(canonical: dict) -> str:
    """서비스 설명 추출"""
    service = get_service_info(canonical)
    return (
        service.get("serviceDescription")
        or service.get("service_description")
        or service.get("what_action")
        or ""
    )


def get_service_name(canonical: dict) -> str:
    """서비스명 추출"""
    service = get_service_info(canonical)
    return (
        service.get("serviceName")
        or service.get("service_name")
        or ""
    )


# ================================
# LLM 초기화
# ================================
def get_llm() -> ChatOpenAI:
    """LLM 인스턴스 생성"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,
    )


# ================================
# 노드 함수들
# ================================
def screen_node(state: EligibilityState) -> dict:
    """규제 스크리닝 노드

    canonical에서 서비스 정보를 추출하여 Rule Screener 실행
    """
    canonical = state["canonical"]

    # canonical에서 서비스 정보 추출 (헬퍼 함수 사용)
    service_description = get_service_description(canonical)
    service_name = get_service_name(canonical)

    # Rule Screener 실행
    result = rule_screener.invoke({
        "service_description": service_description,
        "service_name": service_name,
    })

    logger.info(f"Screening result: {result}")

    # ScreeningResult로 변환
    screening_result = ScreeningResult(
        has_regulation_risk=result.has_regulation_risk,
        risk_signals=result.risk_signals,
        detected_domains=result.detected_domains,
        search_keywords=result.search_keywords,
        confidence=result.confidence,
    )

    return {"screening_result": screening_result}


def search_regulations_node(state: EligibilityState) -> dict:
    """규제제도 검색 노드 (R1)

    스크리닝 결과의 키워드로 규제제도 검색
    """
    screening = state["screening_result"]
    keywords = screening.search_keywords if screening else []

    if not keywords:
        # 키워드 없으면 기본 검색
        service_desc = get_service_description(state["canonical"])
        query = (service_desc or "규제 샌드박스")[:200]
    else:
        query = " ".join(keywords[:5])

    # R1 검색
    result = search_regulation.invoke({
        "query": query,
        "top_k": 5,
    })

    regulations = []
    if hasattr(result, "results"):
        for r in result.results:
            regulations.append({
                "content": r.content,
                "document_title": r.document_title,
                "section_title": r.section_title,
                "track": r.track,
                "citation": r.citation,
                "relevance_score": r.relevance_score,
            })

    logger.info(f"Found {len(regulations)} regulation results")

    return {"regulation_results": regulations}


def search_cases_node(state: EligibilityState) -> dict:
    """승인 사례 검색 노드 (R2)

    서비스 설명으로 유사 승인 사례 검색
    """
    service_description = get_service_description(state["canonical"])

    # R2 검색
    result = search_case.invoke({
        "query": service_description[:500],
        "top_k": 5,
        "deduplicate": True,
    })

    cases = []
    if hasattr(result, "results"):
        for c in result.results:
            cases.append({
                "case_id": c.case_id,
                "company_name": c.company_name,
                "service_name": c.service_name,
                "track": c.track,
                "service_description": c.service_description,
                "current_regulation": c.current_regulation,
                "special_provisions": c.special_provisions,
                "conditions": c.conditions,
                "relevance_score": c.relevance_score,
            })

    logger.info(f"Found {len(cases)} case results")

    return {"case_results": cases}


def search_laws_node(state: EligibilityState) -> dict:
    """도메인별 법령 검색 노드 (R3)

    스크리닝에서 탐지된 도메인으로 법령 검색
    도메인이 없는 경우에도 최소 1회 R3 검색 수행
    """
    screening = state["screening_result"]
    domains = screening.detected_domains if screening else []
    keywords = screening.search_keywords if screening else []

    # 도메인이 없으면 fallback 도메인 사용 (최소 1회 R3 검색 보장)
    if not domains:
        domains = ["data"]  # 기본 도메인 (DOMAIN_MAPPING에 정의됨)

    laws = []

    # 도메인별 검색
    for domain in domains[:2]:  # 최대 2개 도메인
        query = " ".join(keywords[:3]) if keywords else domain
        result = search_domain_law.invoke({
            "query": query,
            "domain": domain,
            "top_k": 3,
        })

        if hasattr(result, "results"):
            for law in result.results:
                laws.append({
                    "law_name": law.law_name,
                    "article_no": law.article_no,
                    "article_title": law.article_title,
                    "content": law.content,
                    "citation": law.citation,
                    "domain": law.domain,
                    "relevance_score": law.relevance_score,
                })

    logger.info(f"Found {len(laws)} law results")

    return {"law_results": laws}


def compose_decision_node(state: EligibilityState) -> dict:
    """판정 통합 노드

    수집된 모든 정보를 종합하여 최종 판정
    """
    screening = state["screening_result"]
    regulations = state["regulation_results"]
    cases = state["case_results"]
    laws = state["law_results"]
    canonical = state["canonical"]

    # canonical의 regulatory_issues 확인
    regulatory = canonical.get("regulatory", {})
    regulatory_issues = regulatory.get("regulatory_issues", [])

    # regulatory_issues에서 unclear 상태 확인
    has_unclear_issue = any(
        issue.get("status") == "unclear" for issue in regulatory_issues
    )

    # regulatory_issues에서 명확한 규제 저촉 확인
    has_blocking_issue = any(
        issue.get("status") in ["blocking", "prohibited", "restricted"]
        for issue in regulatory_issues
    )

    # 유사 승인 사례 여부 판단
    has_similar_case = any(
        c.get("relevance_score", 0) > 0.7 for c in cases
    )

    # 규제 저촉 여부 판단 (고위험 키워드 + 관련 법령 존재)
    has_regulation_conflict = (
        screening.has_regulation_risk if screening else False
    ) and len(laws) > 0

    # Decision Composer 실행
    screening_dict = screening.model_dump() if screening else {}
    result = decision_composer.invoke({
        "screening_result": json.dumps(screening_dict),
        "regulation_count": len(regulations),
        "case_count": len(cases),
        "has_similar_approved_case": has_similar_case,
        "has_regulation_conflict": has_regulation_conflict,
    })

    # LLM으로 상세 분석 (result_summary 생성)
    llm = get_llm()

    prompt = COMPOSE_DECISION_PROMPT.format(
        canonical=json.dumps(state["canonical"], ensure_ascii=False, indent=2),
        screening_result=json.dumps(screening_dict, ensure_ascii=False, indent=2),
        regulation_results=json.dumps(regulations[:3], ensure_ascii=False, indent=2),
        case_results=json.dumps(cases[:3], ensure_ascii=False, indent=2),
        law_results=json.dumps(laws[:3], ensure_ascii=False, indent=2),
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)

    # 응답 파싱 시도
    try:
        response_text = response.content
        # JSON 블록 추출
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        llm_result = json.loads(json_str.strip())
        result_summary = llm_result.get("result_summary", result.reasoning)
    except (json.JSONDecodeError, IndexError):
        result_summary = result.reasoning

    # EligibilityLabel 변환
    label_map = {
        "required": EligibilityLabel.REQUIRED,
        "not_required": EligibilityLabel.NOT_REQUIRED,
        "unclear": EligibilityLabel.UNCLEAR,
    }

    # canonical의 regulatory_issues 상태에 따른 판정 오버라이드
    if has_unclear_issue:
        # unclear 상태가 있으면 UNCLEAR로 판정
        eligibility_label = EligibilityLabel.UNCLEAR
        confidence_score = min(result.confidence_score, 0.6)  # 신뢰도 하향
    elif has_blocking_issue or (has_regulation_conflict and not has_similar_case):
        # 명확한 규제 저촉이 있으면 REQUIRED
        eligibility_label = EligibilityLabel.REQUIRED
        confidence_score = result.confidence_score
    else:
        # 그 외에는 Decision Composer 결과 사용
        eligibility_label = label_map.get(result.eligibility_label, EligibilityLabel.UNCLEAR)
        confidence_score = result.confidence_score

    return {
        "eligibility_label": eligibility_label,
        "confidence_score": confidence_score,
        "result_summary": result_summary,
    }


def generate_evidence_node(state: EligibilityState) -> dict:
    """근거 데이터 생성 노드

    RAG 결과를 evidence_data 형식으로 변환
    """
    regulations = state["regulation_results"]
    cases = state["case_results"]
    laws = state["law_results"]
    screening = state["screening_result"]

    # judgment_summary 생성
    judgment_summary: list[JudgmentSummary] = []

    # 규제제도 기반 근거
    for reg in regulations[:2]:
        judgment_summary.append(JudgmentSummary(
            type=JudgmentType.REGULATION,
            title=reg.get("section_title", "규제 기준"),
            summary=reg.get("content", "")[:200],
            source=reg.get("citation", ""),
        ))

    # 사례 기반 근거
    for case in cases[:2]:
        service_name = case.get("service_name") or "유사 서비스"
        track = case.get("track") or ""
        company = case.get("company_name") or "기업"
        case_id = case.get("case_id") or ""
        description = case.get("service_description") or ""

        judgment_summary.append(JudgmentSummary(
            type=JudgmentType.CASE,
            title=f"{service_name} ({track})" if track else service_name,
            summary=description[:200] if description else "유사 사례 참고",
            source=f"{company} - {case_id}" if case_id else company,
        ))

    # 법령 기반 근거
    for law in laws[:2]:
        judgment_summary.append(JudgmentSummary(
            type=JudgmentType.LAW,
            title=law.get("citation", law.get("law_name", "")),
            summary=law.get("content", "")[:200],
            source=f"{law.get('law_name', '')} {law.get('article_no', '')}",
        ))

    # approval_cases 생성 (Step 2,3,4 재사용)
    approval_cases: list[ApprovalCase] = []
    for case in cases[:5]:
        # ChromaDB distance → similarity 변환 (distance가 낮을수록 유사도 높음)
        distance = case.get("relevance_score", 1.0)
        # 변환 공식: similarity = 1 / (1 + distance) * 100
        similarity = int(100 / (1 + distance)) if distance is not None else 0

        approval_cases.append(ApprovalCase(
            track=case.get("track") or "실증특례",
            date="",  # 데이터에 없으면 빈 문자열
            similarity=similarity,
            title=case.get("service_name") or "유사 서비스",
            company=case.get("company_name") or "기업",
            summary=(case.get("service_description") or "")[:300],
            detail_url=None,
        ))

    # regulations 생성 (Step 2,3,4 재사용)
    regulation_list: list[Regulation] = []
    for reg in regulations[:5]:
        regulation_list.append(Regulation(
            category=reg.get("track", "참고"),
            title=reg.get("section_title", reg.get("document_title", "")),
            summary=reg.get("content", "")[:300],
            source_url=None,
        ))

    # 법령도 regulations에 추가
    for law in laws[:3]:
        regulation_list.append(Regulation(
            category="법령",
            title=law.get("citation", law.get("law_name", "")),
            summary=law.get("content", "")[:300],
            source_url=None,
        ))

    # direct_launch_risks 생성
    direct_launch_risks: list[DirectLaunchRisk] = []
    risk_signals = screening.risk_signals if screening else []

    for signal in risk_signals[:3]:
        direct_launch_risks.append(DirectLaunchRisk(
            type=ReasonType.NEGATIVE,
            title="규제 저촉 가능성",
            description=signal,
            source=None,
        ))

    return {
        "judgment_summary": judgment_summary,
        "approval_cases": approval_cases,
        "regulations": regulation_list,
        "direct_launch_risks": direct_launch_risks,
    }
