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

from .prompts import (
    COMPOSE_DECISION_PROMPT,
    EXPLAIN_CASE_PROMPT,
    EXPLAIN_LAW_PROMPT,
    R1_JUDGMENT_TEMPLATES,
    R1_SANDBOX_REQUIREMENTS,
    SYSTEM_PROMPT,
)
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


def clean_rag_content(text: str, max_length: int = 200) -> str:
    """RAG 검색 결과 텍스트 정리

    - 연속 중복 문자 제거 (① ① → ①)
    - 마크다운 테이블 제거
    - 불필요한 공백 정리
    - 톤 완화 (단정적 표현 → 검토 가능성 표현)
    - 길이 제한
    """
    import re

    if not text:
        return ""

    # 마크다운 테이블 제거 (|---|---| 패턴)
    text = re.sub(r'\|[-]+\|[-|]+\|?', '', text)
    # 테이블 셀 구분자를 쉼표로 변환
    text = re.sub(r'\s*\|\s*', ', ', text)
    # 앞뒤 쉼표 정리
    text = re.sub(r'^,\s*|,\s*$', '', text)
    text = re.sub(r',\s*,', ',', text)

    # 연속 중복 문자 제거 (① ① → ①, 1. 1. → 1.)
    text = re.sub(r'([①-⑳㉠-㉻])\s*\1', r'\1', text)
    text = re.sub(r'(\d+\.)\s*\1', r'\1', text)

    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)

    # 톤 완화: 단정적 표현 → 검토 가능성 표현
    # "적용됩니다" → "검토될 수 있습니다"
    text = re.sub(r'적용됩니다', '검토될 수 있습니다', text)
    # "해당됩니다" → "해당될 수 있습니다"
    text = re.sub(r'해당됩니다', '해당될 수 있습니다', text)
    # "필요합니다" (규제 맥락) → "필요할 수 있습니다"
    text = re.sub(r'신청이 필요합니다', '신청이 필요할 수 있습니다', text)

    # 앞뒤 공백 제거
    text = text.strip()

    # 길이 제한 (문장 단위로 자르기)
    if len(text) > max_length:
        # max_length 근처에서 문장 끝 찾기
        cut_point = text.rfind('.', 0, max_length)
        if cut_point > max_length * 0.5:
            text = text[:cut_point + 1]
        else:
            text = text[:max_length] + "..."

    return text


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


def get_fast_llm() -> ChatOpenAI:
    """빠른 LLM 인스턴스 (설명 생성용)"""
    return ChatOpenAI(
        model="gpt-4o-mini",  # 빠르고 저렴한 모델
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY,
    )


# ================================
# 사례/법령 설명 생성 함수
# ================================
def generate_case_explanation(
    target_service: str,
    case: dict,
) -> str:
    """LLM으로 사례 설명 생성"""
    llm = get_fast_llm()

    prompt = EXPLAIN_CASE_PROMPT.format(
        target_service=target_service,
        case_service_name=case.get("service_name") or "서비스",
        case_company=case.get("company_name") or "기업",
        case_track=case.get("track") or "실증특례",
        case_description=case.get("service_description") or "정보 없음",
        case_regulation=case.get("current_regulation") or "정보 없음",
        case_special_provisions=case.get("special_provisions") or "정보 없음",
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"사례 설명 생성 실패: {e}")
        # fallback
        company = case.get("company_name") or "기업"
        service_name = case.get("service_name") or "서비스"
        track = case.get("track") or "실증특례"
        return f"{company}의 {service_name}가 {track}으로 승인된 유사 사례입니다."


def generate_law_explanation(
    target_service: str,
    law: dict,
) -> str:
    """LLM으로 법령 설명 생성"""
    llm = get_fast_llm()

    prompt = EXPLAIN_LAW_PROMPT.format(
        target_service=target_service,
        law_name=law.get("law_name") or "법령",
        article_no=law.get("article_no") or "",
        article_title=law.get("article_title") or "",
        law_content=law.get("content") or "조문 내용 없음",
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"법령 설명 생성 실패: {e}")
        # fallback
        law_name = law.get("law_name") or "법령"
        article_no = law.get("article_no") or ""
        return f"{law_name} {article_no}에 따라 해당 서비스의 규제 적용 여부를 확인할 필요가 있습니다."


# ================================
# 노드 함수들
# ================================
def screen_node(state: EligibilityState) -> dict:
    """규제 스크리닝 노드

    canonical에서 서비스 정보를 추출하여 Rule Screener 실행
    """
    print("[Step 1/5] 규제 스크리닝 시작...")
    canonical = state["canonical"]

    # canonical에서 서비스 정보 추출 (헬퍼 함수 사용)
    service_description = get_service_description(canonical)
    service_name = get_service_name(canonical)

    # Rule Screener 실행
    result = rule_screener.invoke({
        "service_description": service_description,
        "service_name": service_name,
    })

    print(f"[Step 1/5] 규제 스크리닝 완료 - 리스크: {result.has_regulation_risk}, 도메인: {result.detected_domains}")

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
    """규제제도 참조 노드 (R1)

    R1은 제도 중심 고정 쿼리로 검색합니다.
    도메인 키워드가 아닌, 규제샌드박스 제도/기준 관련 쿼리만 사용합니다.
    """
    print("[Step 2/5] R1 규제제도 검색 시작...")
    # R1 고정 쿼리 (도메인 키워드 사용 금지)
    # 이 쿼리는 R1 데이터의 의미 공간(제도/요건/절차)에 맞춰져 있음
    R1_FIXED_QUERY = """규제샌드박스 신속확인 실증특례 임시허가 대상 기준
법령 적용 여부 불명확 규제 공백 신기술 서비스"""

    # R1 RAG 검색 실행
    result = search_regulation.invoke({
        "query": R1_FIXED_QUERY,
        "top_k": 5,
    })

    regulations = []
    if hasattr(result, "results") and result.results:
        for reg in result.results:
            regulations.append({
                "content": reg.content,
                "document_title": reg.document_title,
                "section_title": reg.section_title,
                "track": reg.track,
                "citation": reg.citation,
                "relevance_score": reg.relevance_score,
            })
        print(f"[Step 2/5] R1 규제제도 검색 완료 - {len(regulations)}건")
    else:
        # 검색 결과 없으면 fallback 고정 템플릿 사용
        regulations = [
            {
                "content": R1_SANDBOX_REQUIREMENTS,
                "document_title": "ICT 규제샌드박스 제도 가이드",
                "section_title": "규제샌드박스 신청 요건",
                "track": "all",
                "citation": "ICT 규제샌드박스 제도 가이드",
                "relevance_score": 1.0,
            }
        ]
        print("[Step 2/5] R1 검색 결과 없음, fallback 템플릿 사용")

    return {"regulation_results": regulations}


def search_cases_node(state: EligibilityState) -> dict:
    """승인 사례 검색 노드 (R2)

    서비스 설명으로 유사 승인 사례 검색
    """
    print("[Step 3/5] R2 승인 사례 검색 시작...")
    service_description = get_service_description(state["canonical"])
    query = (service_description or "규제 샌드박스 서비스")[:500]

    # R2 검색
    result = search_case.invoke({
        "query": query,
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
                "source_url": c.source_url,  # 사례 상세 URL
            })

    print(f"[Step 3/5] R2 승인 사례 검색 완료 - {len(cases)}건")

    return {"case_results": cases}


def search_laws_node(state: EligibilityState) -> dict:
    """도메인별 법령 검색 노드 (R3)

    스크리닝에서 탐지된 도메인으로 법령 검색
    도메인이 없는 경우에도 최소 1회 R3 검색 수행
    """
    print("[Step 4/5] R3 법령 검색 시작...")
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

    print(f"[Step 4/5] R3 법령 검색 완료 - {len(laws)}건")

    return {"law_results": laws}


def compose_decision_node(state: EligibilityState) -> dict:
    """판정 통합 노드

    수집된 모든 정보를 종합하여 최종 판정
    """
    print("[Step 5/5] LLM 판정 통합 시작...")
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

    # 유사 승인 사례 여부 판단 (relevance_score는 distance - 낮을수록 유사)
    # similarity = 1 / (1 + distance), 50% 이상이면 유사 사례로 판단
    has_similar_case = any(
        (1 / (1 + c.get("relevance_score", 1.0))) > 0.5 for c in cases
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

    print("[Step 5/5] LLM 호출 중...")
    response = llm.invoke(messages)
    print("[Step 5/5] LLM 응답 수신 완료")

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
    R1/R2/R3 검색 결과 사용, R1 결과 없으면 fallback 템플릿 사용
    LLM으로 사례/법령 설명 생성
    """
    print("[Evidence] 근거 데이터 생성 시작...")
    cases = state["case_results"]
    laws = state["law_results"]
    regulations = state["regulation_results"]
    screening = state["screening_result"]
    eligibility_label = state.get("eligibility_label")
    canonical = state["canonical"]

    # 분석 대상 서비스 정보 (LLM 설명 생성용)
    target_service = get_service_description(canonical) or get_service_name(canonical) or "분석 대상 서비스"

    # judgment_summary 생성
    judgment_summary: list[JudgmentSummary] = []

    # 규제 기준: R1 RAG 검색 결과 사용, 없으면 fallback 템플릿
    if regulations:
        for reg in regulations[:2]:  # 최대 2개
            judgment_summary.append(JudgmentSummary(
                type=JudgmentType.REGULATION,
                title=reg.get("section_title") or reg.get("document_title") or "규제 기준",
                summary=clean_rag_content(reg.get("content", ""), max_length=200),
                source=reg.get("citation") or reg.get("document_title") or "ICT 규제샌드박스",
            ))
    else:
        # fallback: 고정 템플릿 사용
        label_key = eligibility_label.value if eligibility_label else "unclear"
        r1_templates = R1_JUDGMENT_TEMPLATES.get(label_key, R1_JUDGMENT_TEMPLATES["unclear"])

        for template in r1_templates:
            judgment_summary.append(JudgmentSummary(
                type=JudgmentType.REGULATION,
                title=template["title"],
                summary=template["summary"],
                source=template["source"],
            ))

    # 사례 기반 근거 (LLM으로 설명 생성)
    print(f"[Evidence] 사례 설명 LLM 생성 중... ({len(cases[:2])}건)")
    for i, case in enumerate(cases[:2]):
        print(f"[Evidence] 사례 {i+1}/{len(cases[:2])} 설명 생성 중...")
        service_name = case.get("service_name") or "유사 서비스"
        track = case.get("track") or ""
        company = case.get("company_name") or "기업"
        case_id = case.get("case_id") or ""

        # LLM으로 사례 설명 생성 (유사점, 참고 이유 포함)
        case_summary = generate_case_explanation(target_service, case)

        judgment_summary.append(JudgmentSummary(
            type=JudgmentType.CASE,
            title=f"{service_name} ({track})" if track else service_name,
            summary=clean_rag_content(case_summary, max_length=250),
            source=f"{company} - {case_id}" if case_id else company,
        ))
    print("[Evidence] 사례 설명 생성 완료")

    # 법령 기반 근거 (LLM으로 설명 생성)
    print(f"[Evidence] 법령 설명 LLM 생성 중... ({len(laws[:2])}건)")
    for i, law in enumerate(laws[:2]):
        print(f"[Evidence] 법령 {i+1}/{len(laws[:2])} 설명 생성 중...")
        law_name = law.get("law_name", "")
        article_no = law.get("article_no", "")
        citation = law.get("citation") or f"{law_name} {article_no}"

        # LLM으로 법령 설명 생성 (조문 의미, 검토 필요성 포함)
        law_summary = generate_law_explanation(target_service, law)

        judgment_summary.append(JudgmentSummary(
            type=JudgmentType.LAW,
            title=citation,
            summary=clean_rag_content(law_summary, max_length=250),
            source=f"{law_name} {article_no}".strip(),
        ))
    print("[Evidence] 법령 설명 생성 완료")

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
            summary=clean_rag_content(case.get("service_description") or "", max_length=300),
            detail_url=case.get("source_url"),  # 규제샌드박스 포털 링크
        ))

    # regulations 생성 (Step 2,3,4 재사용)
    regulation_list: list[Regulation] = []
    for reg in regulations[:5]:
        regulation_list.append(Regulation(
            category=reg.get("track", "참고"),
            title=reg.get("section_title", reg.get("document_title", "")),
            summary=clean_rag_content(reg.get("content", ""), max_length=300),
            source_url=None,
        ))

    # 법령도 regulations에 추가
    for law in laws[:3]:
        regulation_list.append(Regulation(
            category="법령",
            title=law.get("citation", law.get("law_name", "")),
            summary=clean_rag_content(law.get("content", ""), max_length=300),
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

    print("[Evidence] 근거 데이터 생성 완료")
    return {
        "judgment_summary": judgment_summary,
        "approval_cases": approval_cases,
        "regulations": regulation_list,
        "direct_launch_risks": direct_launch_risks,
    }
