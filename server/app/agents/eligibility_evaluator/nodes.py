"""Eligibility Evaluator 노드 함수

그래프의 각 단계 로직을 정의합니다.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_fast_llm, get_llm
from app.tools.shared.rag.case_rag import search_case
from app.tools.shared.rag.domain_law_rag import DOMAIN_MAPPING, search_domain_law
from app.tools.shared.rag.regulation_rag import search_regulation

from .prompts import (
    COMPOSE_DECISION_PROMPT,
    EXPLAIN_CASE_PROMPT,
    EXPLAIN_LAW_PROMPT,
    EXPLAIN_REGULATION_PROMPT,
    R1_SANDBOX_REQUIREMENTS,
    SYSTEM_PROMPT,
)
from .schemas import (
    ApprovalCase,
    DirectLaunchRisk,
    EligibilityLabel,
    JudgmentSummary,
    JudgmentType,
    Regulation,
)
from .state import EligibilityState, ScreeningResult
from .tools import rule_screener

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

    # 이스케이프된 줄바꿈을 실제 줄바꿈으로 변환
    text = text.replace("\\n", "\n")

    # 마크다운 코드블록 백틱 제거
    text = re.sub(r"```\w*", "", text)
    text = text.replace("`", "")

    # 마크다운 테이블 구분선 제거 (|---|---|)
    text = re.sub(r"\|[-:]+\|[-:|]+\|?", "", text)
    # 빈 테이블 행 제거 (||, | |)
    text = re.sub(r"^\s*\|\s*\|\s*$", "", text, flags=re.MULTILINE)
    # 각 줄의 시작/끝 파이프 제거
    text = re.sub(r"^\s*\|\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*\|\s*$", "", text, flags=re.MULTILINE)
    # 중간 파이프는 쉼표로 변환
    text = re.sub(r"\s*\|\s*", ", ", text)
    # 빈 줄 정리 (연속 빈 줄 → 하나로)
    text = re.sub(r"\n\s*\n+", "\n", text)

    # 연속 중복 문자 제거 (① ① → ①, 1. 1. → 1.)
    text = re.sub(r"([①-⑳㉠-㉻])\s*\1", r"\1", text)
    text = re.sub(r"(\d+\.)\s*\1", r"\1", text)

    # 연속 공백 정리 (줄바꿈은 유지)
    text = re.sub(r"[ \t]+", " ", text)

    # 톤 완화: 단정적 표현 → 검토 가능성 표현
    # "적용됩니다" → "검토될 수 있습니다"
    text = re.sub(r"적용됩니다", "검토될 수 있습니다", text)
    # "해당됩니다" → "해당될 수 있습니다"
    text = re.sub(r"해당됩니다", "해당될 수 있습니다", text)
    # "필요합니다" (규제 맥락) → "필요할 수 있습니다"
    text = re.sub(r"신청이 필요합니다", "신청이 필요할 수 있습니다", text)

    # 앞뒤 공백 제거
    text = text.strip()

    # 길이 제한 (문장 단위로 자르기)
    if len(text) > max_length:
        # max_length 근처에서 문장 끝 찾기
        cut_point = text.rfind(".", 0, max_length)
        if cut_point > max_length * 0.5:
            text = text[: cut_point + 1]
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
    return service.get("serviceDescription") or service.get("service_description") or service.get("what_action") or ""


def get_service_name(canonical: dict) -> str:
    """서비스명 추출"""
    service = get_service_info(canonical)
    return service.get("serviceName") or service.get("service_name") or ""


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


def generate_regulation_explanation(
    target_service: str,
    regulation: dict,
) -> str:
    """LLM으로 규제제도 설명 생성"""
    llm = get_fast_llm()

    prompt = EXPLAIN_REGULATION_PROMPT.format(
        target_service=target_service,
        document_title=regulation.get("document_title") or "규제제도",
        section_title=regulation.get("section_title") or "",
        track=regulation.get("track") or "참고",
        regulation_content=regulation.get("content") or "내용 없음",
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        logger.warning(f"규제제도 설명 생성 실패: {e}")
        # fallback
        title = regulation.get("section_title") or regulation.get("document_title") or "규제제도"
        return f"{title}에 따라 해당 서비스의 규제샌드박스 적용 여부를 검토할 필요가 있습니다."


# ================================
# 노드 함수들
# ================================
def screen_node(state: EligibilityState) -> dict:
    """규제 스크리닝 노드

    canonical에서 서비스 정보를 추출하여 Rule Screener 실행
    """
    start_time = time.time()
    print("[Step2-1/4] 규제 스크리닝 시작...")
    canonical = state.get("canonical", {})

    # canonical에서 서비스 정보 추출 (헬퍼 함수 사용)
    service_description = get_service_description(canonical)
    service_name = get_service_name(canonical)

    # Rule Screener 실행
    result = rule_screener.invoke(
        {
            "service_description": service_description,
            "service_name": service_name,
        }
    )

    elapsed = time.time() - start_time
    print(f"[Step2-1/4] 규제 스크리닝 완료 ({elapsed:.2f}초) - 리스크: {result.has_regulation_risk}, 도메인: {result.detected_domains}")

    # ScreeningResult로 변환
    screening_result = ScreeningResult(
        has_regulation_risk=result.has_regulation_risk,
        risk_signals=result.risk_signals,
        detected_domains=result.detected_domains,
        search_keywords=result.search_keywords,
        confidence=result.confidence,
    )

    return {"screening_result": screening_result}


def _search_regulations(screening) -> list[dict]:
    """R1 규제제도 검색 (내부 함수)

    Note: 서비스 키워드를 쿼리에 포함하면 임베딩 유사도가 떨어지므로
    제도 관련 키워드만 사용하여 검색합니다.
    """
    # 서비스 키워드 제외, 제도 검색에 최적화된 쿼리 사용
    query = "규제샌드박스 실증특례 임시허가 신청 요건 절차"

    result = search_regulation.invoke({"query": query, "top_k": 5})

    regulations = []
    if hasattr(result, "results") and result.results:
        for reg in result.results:
            regulations.append({
                "content": reg.content,
                "document_title": reg.document_title,
                "section_title": reg.section_title,
                "track": reg.track,
                "citation": reg.citation,
                "source_url": reg.source_url,
                "relevance_score": reg.relevance_score,
            })
    else:
        regulations = [{
            "content": R1_SANDBOX_REQUIREMENTS,
            "document_title": "ICT 규제샌드박스 제도 가이드",
            "section_title": "규제샌드박스 신청 요건",
            "track": "all",
            "citation": "ICT 규제샌드박스 제도 가이드",
            "relevance_score": 1.0,
            "source_url": "https://www.sandbox.or.kr/guidance/intro.do",
        }]

    return regulations


def _search_cases(canonical: dict) -> list[dict]:
    """R2 승인 사례 검색 (내부 함수)"""
    service_description = get_service_description(canonical)
    query = (service_description or "규제 샌드박스 서비스")[:500]

    result = search_case.invoke({"query": query, "top_k": 5, "deduplicate": True})

    cases = []
    if hasattr(result, "results"):
        for c in result.results:
            cases.append({
                "case_id": c.case_id,
                "company_name": c.company_name,
                "service_name": c.service_name,
                "track": c.track,
                "designation_date": c.designation_date,
                "service_description": c.service_description,
                "current_regulation": c.current_regulation,
                "special_provisions": c.special_provisions,
                "conditions": c.conditions,
                "relevance_score": c.relevance_score,
                "source_url": c.source_url,
            })

    return cases


def _search_laws(screening) -> list[dict]:
    """R3 도메인별 법령 검색 (내부 함수)

    DOMAIN_MAPPING에 있는 도메인만 검색, 없으면 빈 결과 반환
    """
    domains = screening.detected_domains if screening else []
    keywords = screening.search_keywords if screening else []

    # DOMAIN_MAPPING에 있는 도메인만 필터링 (매핑 안 된 도메인은 검색 안 함)
    valid_domains = [d for d in domains if d.lower() in DOMAIN_MAPPING]

    if not valid_domains:
        return []

    laws = []
    for domain in valid_domains[:3]:
        query = " ".join(keywords[:3]) if keywords else domain
        result = search_domain_law.invoke({"query": query, "domain": domain, "top_k": 3})

        if hasattr(result, "results"):
            for law in result.results:
                laws.append({
                    "law_name": law.law_name,
                    "article_no": law.article_no,
                    "article_title": law.article_title,
                    "content": law.content,
                    "citation": law.citation,
                    "domain": law.domain,
                    "domain_label": law.domain_label,
                    "source_url": law.source_url,
                    "relevance_score": law.relevance_score,
                })

    return laws


def search_all_rag_node(state: EligibilityState) -> dict:
    """RAG 검색 통합 노드 (R1 + R2 + R3 병렬 실행)

    규제제도, 승인 사례, 도메인 법령을 병렬로 검색합니다.
    """
    start_time = time.time()
    print("[Step2-2/4] RAG 검색 병렬 실행 시작 (R1 + R2 + R3)...")
    screening = state.get("screening_result")
    canonical = state.get("canonical", {})

    regulations = []
    cases = []
    laws = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_regs = executor.submit(_search_regulations, screening)
        future_cases = executor.submit(_search_cases, canonical)
        future_laws = executor.submit(_search_laws, screening)

        try:
            regulations = future_regs.result()
            print(f"[Step2-2/4] R1 규제제도 검색 완료 - {len(regulations)}건")
        except Exception as e:
            logger.warning(f"R1 검색 실패: {e}")

        try:
            cases = future_cases.result()
            print(f"[Step2-2/4] R2 승인 사례 검색 완료 - {len(cases)}건")
        except Exception as e:
            logger.warning(f"R2 검색 실패: {e}")

        try:
            laws = future_laws.result()
            print(f"[Step2-2/4] R3 법령 검색 완료 - {len(laws)}건")
        except Exception as e:
            logger.warning(f"R3 검색 실패: {e}")

    elapsed = time.time() - start_time
    print(f"[Step2-2/4] RAG 검색 병렬 실행 완료 ({elapsed:.2f}초)")

    return {
        "regulation_results": regulations,
        "case_results": cases,
        "law_results": laws,
    }


# 기존 노드 함수들 (하위 호환성 유지)
def search_regulations_node(state: EligibilityState) -> dict:
    """규제제도 참조 노드 (R1) - deprecated, search_all_rag_node 사용 권장"""
    screening = state.get("screening_result")
    return {"regulation_results": _search_regulations(screening)}


def search_cases_node(state: EligibilityState) -> dict:
    """승인 사례 검색 노드 (R2) - deprecated, search_all_rag_node 사용 권장"""
    return {"case_results": _search_cases(state.get("canonical", {}))}


def search_laws_node(state: EligibilityState) -> dict:
    """도메인별 법령 검색 노드 (R3) - deprecated, search_all_rag_node 사용 권장"""
    screening = state.get("screening_result")
    return {"law_results": _search_laws(screening)}


def compose_decision_node(state: EligibilityState) -> dict:
    """판정 통합 노드

    수집된 모든 정보를 종합하여 최종 판정
    """
    start_time = time.time()
    print("[Step2-3/4] LLM 판정 통합 시작...")
    screening = state.get("screening_result")
    regulations = state.get("regulation_results", [])
    cases = state.get("case_results", [])
    laws = state.get("law_results", [])

    # LLM으로 상세 분석 (canonical + RAG 결과만으로 판단)
    screening_dict = screening.model_dump() if screening else {}
    llm = get_llm()

    prompt = COMPOSE_DECISION_PROMPT.format(
        canonical=json.dumps(state.get("canonical", {}), ensure_ascii=False, indent=2),
        screening_result=json.dumps(screening_dict, ensure_ascii=False, indent=2),
        regulation_results=json.dumps(regulations[:3], ensure_ascii=False, indent=2),
        case_results=json.dumps(cases[:3], ensure_ascii=False, indent=2),
        law_results=json.dumps(laws[:3], ensure_ascii=False, indent=2),
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    llm_start = time.time()
    print("[Step2-3/4] LLM 호출 중...")
    response = llm.invoke(messages)
    llm_elapsed = time.time() - llm_start
    print(f"[Step2-3/4] LLM 응답 수신 완료 ({llm_elapsed:.2f}초)")

    # 응답 파싱 시도
    direct_launch_risks: list[DirectLaunchRisk] = []
    llm_result: dict = {}  # 파싱 실패 시 기본값
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
        result_summary = llm_result.get("result_summary", "")

        # direct_launch_risks 파싱
        raw_risks = llm_result.get("direct_launch_risks", [])
        print(f"[DEBUG] LLM eligibility_label: {llm_result.get('eligibility_label')}")
        print(f"[DEBUG] LLM raw_risks: {raw_risks}")
        for risk in raw_risks[:3]:  # 최대 3개
            direct_launch_risks.append(
                DirectLaunchRisk(
                    title=risk.get("title", "규제 리스크"),
                    description=risk.get("description", ""),
                    source=risk.get("source"),
                )
            )
        print(f"[Step 5/5] direct_launch_risks 파싱 완료: {len(direct_launch_risks)}개")
    except (json.JSONDecodeError, IndexError):
        result_summary = "판정 결과를 파싱할 수 없습니다."

    # EligibilityLabel 변환 - LLM 결과를 그대로 사용
    label_map = {
        "required": EligibilityLabel.REQUIRED,
        "not_required": EligibilityLabel.NOT_REQUIRED,
        "unclear": EligibilityLabel.UNCLEAR,
    }

    # LLM이 반환한 eligibility_label 사용 (오버라이드 없음)
    llm_label = llm_result.get("eligibility_label", "unclear")
    eligibility_label = label_map.get(llm_label, EligibilityLabel.UNCLEAR)

    # ==============================
    # 규칙 기반 confidence_score 계산
    # LLM 신뢰도 대신 측정 가능한 지표 사용
    # ==============================
    regulation_count = len(regulations)
    case_count = len(cases)
    law_count = len(laws)
    evidence_count = regulation_count + case_count + law_count
    has_risk = screening.has_regulation_risk if screening else False

    # 판정 유형별 기본 신뢰도
    if llm_label == "required" and regulation_count > 0:
        base_confidence = 0.85  # 규제 저촉 + 근거 있음
    elif llm_label == "not_required" and case_count > 0 and not has_risk:
        base_confidence = 0.80  # 유사 승인 사례 O, 리스크 X
    elif llm_label == "required" and has_risk:
        base_confidence = 0.75  # 리스크 감지됨
    elif llm_label == "unclear" and evidence_count == 0:
        base_confidence = 0.50  # 정보 부족
    else:
        base_confidence = 0.60  # 기타

    # 정보량에 따른 보정 (규제+사례: 0.02, 법령: 0.01, 최대 +0.1)
    info_bonus = min(
        (regulation_count + case_count) * 0.02 + law_count * 0.01,
        0.1
    )
    confidence_score = min(base_confidence + info_bonus, 0.95)

    # 상한 cap: 근거 부족하거나 불명확하면 제한
    if evidence_count < 2:
        confidence_score = min(confidence_score, 0.7)
    if llm_label == "unclear":
        confidence_score = min(confidence_score, 0.65)

    print(f"[Step2-3/4] 신뢰도 계산: base={base_confidence}, bonus={info_bonus:.2f}, "
          f"evidence={evidence_count}, final={confidence_score:.2f}")

    elapsed = time.time() - start_time
    print(f"[Step2-3/4] LLM 판정 통합 완료 ({elapsed:.2f}초)")

    return {
        "eligibility_label": eligibility_label,
        "confidence_score": confidence_score,
        "result_summary": result_summary,
        "direct_launch_risks": direct_launch_risks,
    }


def generate_evidence_node(state: EligibilityState) -> dict:
    """근거 데이터 생성 노드

    RAG 결과를 evidence_data 형식으로 변환
    R1/R2/R3 검색 결과 사용, R1 결과 없으면 fallback 템플릿 사용
    LLM으로 사례/법령 설명 생성 (병렬 처리)
    """
    start_time = time.time()
    print("[Step2-4/4] 근거 데이터 생성 시작...")
    cases = state.get("case_results", [])
    laws = state.get("law_results", [])
    regulations = state.get("regulation_results", [])
    canonical = state.get("canonical", {})

    # 분석 대상 서비스 정보 (LLM 설명 생성용)
    target_service = get_service_description(canonical) or get_service_name(canonical) or "분석 대상 서비스"

    # judgment_summary 생성 (R1 규제 기준 + R2 사례 + R3 법령)
    judgment_summary: list[JudgmentSummary] = []

    # 병렬 처리를 위한 작업 목록 생성
    reg_items = regulations[:3]
    case_items = cases[:3]
    law_items = laws[:3]

    total_tasks = len(reg_items) + len(case_items) + len(law_items)
    print(f"[Step2-4/4] LLM 설명 생성 병렬 처리 시작 ({total_tasks}건)...")

    # 결과 저장용 딕셔너리
    reg_summaries: dict[int, str] = {}
    case_summaries: dict[int, str] = {}
    law_summaries: dict[int, str] = {}

    # ThreadPoolExecutor로 병렬 처리
    with ThreadPoolExecutor(max_workers=9) as executor:
        futures = {}

        # 규제제도 설명 생성 작업 제출
        for i, reg in enumerate(reg_items):
            future = executor.submit(generate_regulation_explanation, target_service, reg)
            futures[future] = ("reg", i)

        # 사례 설명 생성 작업 제출
        for i, case in enumerate(case_items):
            future = executor.submit(generate_case_explanation, target_service, case)
            futures[future] = ("case", i)

        # 법령 설명 생성 작업 제출
        for i, law in enumerate(law_items):
            future = executor.submit(generate_law_explanation, target_service, law)
            futures[future] = ("law", i)

        # 완료된 작업 수집
        for future in as_completed(futures):
            task_type, idx = futures[future]
            try:
                result = future.result()
                if task_type == "reg":
                    reg_summaries[idx] = result
                elif task_type == "case":
                    case_summaries[idx] = result
                elif task_type == "law":
                    law_summaries[idx] = result
            except Exception as e:
                logger.warning(f"{task_type} 설명 생성 실패 (idx={idx}): {e}")
                if task_type == "reg":
                    reg_summaries[idx] = "규제제도 설명을 생성할 수 없습니다."
                elif task_type == "case":
                    case_summaries[idx] = "사례 설명을 생성할 수 없습니다."
                elif task_type == "law":
                    law_summaries[idx] = "법령 설명을 생성할 수 없습니다."

    llm_elapsed = time.time() - start_time
    print(f"[Step2-4/4] LLM 설명 생성 병렬 처리 완료 ({llm_elapsed:.2f}초)")

    # 규제 기준 (R1) 결과 조합
    for i, reg in enumerate(reg_items):
        reg_summary = reg_summaries.get(i, "")
        judgment_summary.append(
            JudgmentSummary(
                type=JudgmentType.REGULATION,
                title=reg.get("section_title") or reg.get("document_title") or "규제 기준",
                summary=clean_rag_content(reg_summary, max_length=250),
                source=reg.get("citation") or reg.get("document_title") or "ICT 규제샌드박스",
                source_url=reg.get("source_url"),
            )
        )

    # 사례 기반 근거 결과 조합
    for i, case in enumerate(case_items):
        service_name = case.get("service_name") or case.get("case_id") or "유사 서비스"
        track = case.get("track") or ""
        company = case.get("company_name") or "기업"
        case_id = case.get("case_id") or ""
        case_summary = case_summaries.get(i, "")
        case_source_url = case.get("source_url")

        judgment_summary.append(
            JudgmentSummary(
                type=JudgmentType.CASE,
                title=f"{service_name} ({track})" if track else service_name,
                summary=clean_rag_content(case_summary, max_length=250),
                source=f"{company} - {case_id}" if case_id else company,
                source_url=case_source_url,
            )
        )

    # 법령 기반 근거 결과 조합
    for i, law in enumerate(law_items):
        law_name = law.get("law_name", "")
        article_no = law.get("article_no", "")
        citation = law.get("citation") or f"{law_name} {article_no}"
        law_summary = law_summaries.get(i, "")

        judgment_summary.append(
            JudgmentSummary(
                type=JudgmentType.LAW,
                title=citation,
                summary=clean_rag_content(law_summary, max_length=250),
                source=f"{law_name} {article_no}".strip(),
                source_url=law.get("source_url"),
            )
        )

    # approval_cases 생성 (Step 2,3,4 재사용)
    approval_cases: list[ApprovalCase] = []
    for case in cases[:5]:
        # ChromaDB distance → similarity 변환 (distance가 낮을수록 유사도 높음)
        distance = case.get("relevance_score", 1.0)
        # 변환 공식: similarity = 1 / (1 + distance) * 100
        similarity = int(100 / (1 + distance)) if distance is not None else 0

        approval_cases.append(
            ApprovalCase(
                track=case.get("track") or "실증특례",
                date=case.get("designation_date") or "",
                similarity=similarity,
                title=case.get("service_name") or case.get("case_id") or "유사 서비스",
                company=case.get("company_name") or "기업",
                summary=clean_rag_content(case.get("service_description") or "", max_length=300),
                source_url=case.get("source_url"),  # 규제샌드박스 포털 링크
            )
        )

    # regulations 생성 (Step 2,3,4 재사용) - 법령 먼저, 제도 나중 (패널 제목: 법령·제도)
    regulation_list: list[Regulation] = []

    # R3 법령 먼저
    for law in laws[:3]:
        domain_label = law.get("domain_label", "")
        category = f"법령·{domain_label}" if domain_label else "법령"
        regulation_list.append(
            Regulation(
                category=category,
                title=law.get("citation", law.get("law_name", "")),
                summary=clean_rag_content(law.get("content", ""), max_length=300),
                source_url=law.get("source_url"),
            )
        )

    # R1 제도 정보
    for reg in regulations[:3]:
        track = reg.get("track", "참고")
        category = "공통" if track == "all" else track
        section_title = reg.get("section_title", reg.get("document_title", ""))
        content = reg.get("content", "")
        # content 시작 부분의 [section_title] 제거 (중복 방지)
        if section_title and content.startswith(f"[{section_title}]"):
            content = content[len(f"[{section_title}]"):].lstrip()
        regulation_list.append(
            Regulation(
                category=category,
                title=section_title,
                summary=clean_rag_content(content, max_length=300),
                source_url=reg.get("source_url"),
            )
        )

    # direct_launch_risks는 compose_decision_node에서 LLM이 생성하여 state에 저장됨
    # 여기서는 생성하지 않음

    elapsed = time.time() - start_time
    print(f"[Step2-4/4] 근거 데이터 생성 완료 ({elapsed:.2f}초)")
    return {
        "judgment_summary": judgment_summary,
        "approval_cases": approval_cases,
        "regulations": regulation_list,
    }
