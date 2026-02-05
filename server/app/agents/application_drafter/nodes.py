"""Application Drafter Agent 노드 함수

접근 방식:
- 트랙에 맞는 폼 스키마를 서버에서 로드
- canonical 데이터를 기반으로 LLM이 폼 필드 값 생성
- 결과를 application_draft로 저장
"""

import json
import logging
import re

from langchain_openai import ChatOpenAI

from app.agents.application_drafter.form_schema import load_form_schema
from app.agents.application_drafter.prompts import (
    DRAFT_SYSTEM_PROMPT,
    DRAFT_USER_PROMPT,
    TRACK_NAME_MAP,
)
from app.agents.application_drafter.state import ApplicationDrafterState
from app.core.config import settings
from app.tools.shared.rag import (
    get_application_requirements,
    get_review_criteria,
    get_similar_cases_for_application,
)

logger = logging.getLogger(__name__)


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY,
    )


def get_service_info(canonical: dict) -> str:
    """canonical에서 서비스 정보 텍스트 추출"""
    parts = []

    company = canonical.get("company", {})
    if company.get("company_name"):
        parts.append(f"회사명: {company['company_name']}")
    if company.get("representative"):
        parts.append(f"대표자: {company['representative']}")
    if company.get("business_number"):
        parts.append(f"사업자등록번호: {company['business_number']}")
    if company.get("address"):
        parts.append(f"주소: {company['address']}")
    if company.get("contact"):
        parts.append(f"전화번호: {company['contact']}")
    if company.get("email"):
        parts.append(f"이메일: {company['email']}")

    service = canonical.get("service", {})
    if service.get("service_name"):
        parts.append(f"서비스명: {service['service_name']}")
    # DEBUG: service_type 확인
    print(f"[DEBUG Draft] canonical.service.service_type = {service.get('service_type')}")
    if service.get("service_type"):
        # HWP에서 파싱된 유형을 폼 값으로 변환
        service_type_raw = service["service_type"]
        service_type_map = {
            "기술인 경우": "technology",
            "기술인경우": "technology",
            "서비스인 경우": "service",
            "서비스인경우": "service",
            "기술과 서비스가 융합된 경우": "technologyAndService",
            "기술과서비스가융합된경우": "technologyAndService",
        }
        # 공백 제거 후 매핑
        service_type_normalized = service_type_raw.replace(" ", "")
        service_type_value = service_type_map.get(service_type_normalized, service_type_raw)
        print(f"[DEBUG Draft] service_type 변환: {service_type_raw} -> {service_type_value}")
        parts.append(f"서비스 유형(type): {service_type_value}")
    if service.get("service_description"):
        parts.append(f"서비스 설명: {service['service_description']}")
    if service.get("what_action"):
        parts.append(f"핵심 행위: {service['what_action']}")
    if service.get("target_users"):
        parts.append(f"대상 이용자: {service['target_users']}")
    if service.get("delivery_method"):
        parts.append(f"제공 방식: {service['delivery_method']}")

    technology = canonical.get("technology", {})
    if technology.get("core_technology"):
        parts.append(f"핵심 기술: {technology['core_technology']}")
    if technology.get("innovation_points"):
        points = technology["innovation_points"]
        if isinstance(points, list):
            parts.append(f"혁신 포인트: {', '.join(points)}")

    regulatory = canonical.get("regulatory", {})
    if regulatory.get("related_regulations"):
        regs = regulatory["related_regulations"]
        if isinstance(regs, list):
            parts.append(f"관련 규제: {', '.join(regs)}")
    if regulatory.get("regulatory_issues"):
        issues = regulatory["regulatory_issues"]
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, dict) and issue.get("summary"):
                    parts.append(f"규제 이슈: {issue['summary']}")

    return "\n".join(parts) if parts else "서비스 정보 없음"


def get_service_description(canonical: dict) -> str:
    """canonical에서 서비스 설명 추출 (RAG 검색용)"""
    service = canonical.get("service", {})
    desc = service.get("service_description", "")
    name = service.get("service_name", "")
    return f"{name} - {desc}" if name and desc else desc or name or ""


def clean_rag_content(content: str) -> str:
    """RAG 결과의 불필요한 문자 정리"""
    if not content:
        return ""
    content = content.replace("\\n", "\n").strip()
    return content[:2000]


def format_rag_results(results: list[dict], max_items: int = 5) -> str:
    """RAG 결과를 텍스트로 포맷팅"""
    if not results:
        return "관련 정보 없음"

    parts = []
    for i, item in enumerate(results[:max_items]):
        content = item.get("content", "")
        metadata = item.get("metadata", {})
        title = metadata.get("title", f"항목 {i+1}")
        cleaned = clean_rag_content(content)
        parts.append(f"[{title}]\n{cleaned}")

    return "\n\n".join(parts)


# ===============================
# Node 1: 폼 스키마 로드
# ===============================

async def load_form_schema_node(state: ApplicationDrafterState) -> dict:
    """트랙에 맞는 폼 스키마 로드"""
    track = state.get("track", "demo")

    try:
        form_schema = load_form_schema(track)
        logger.info("폼 스키마 로드 완료: track=%s, forms=%d", track, len(form_schema))
    except (ValueError, FileNotFoundError) as e:
        logger.error("폼 스키마 로드 실패: %s", e)
        form_schema = {}

    return {"form_schema": form_schema}


# ===============================
# Node 2: RAG 컨텍스트 검색
# ===============================

async def retrieve_context_node(state: ApplicationDrafterState) -> dict:
    """R1/R2 RAG 검색으로 신청서 작성에 필요한 컨텍스트 수집"""
    canonical = state.get("canonical", {})
    track = state.get("track", "demo")
    track_korean = TRACK_NAME_MAP.get(track, "실증특례")

    service_desc = get_service_description(canonical)

    # R1: 신청 요건/작성 가이드
    try:
        app_req_results = get_application_requirements.invoke({"track": track_korean})
        application_requirements = [
            {"content": r.content, "metadata": r.metadata}
            for r in app_req_results
        ]
    except Exception as e:
        logger.warning("R1 신청 요건 검색 실패: %s", e)
        application_requirements = []

    # R1: 심사 기준
    try:
        review_results = get_review_criteria.invoke({"track": track_korean})
        review_criteria = [
            {"content": r.content, "metadata": r.metadata}
            for r in review_results
        ]
    except Exception as e:
        logger.warning("R1 심사 기준 검색 실패: %s", e)
        review_criteria = []

    # R2: 유사 승인 사례
    try:
        if service_desc:
            case_result = get_similar_cases_for_application.invoke({
                "service_description": service_desc,
                "track": track_korean,
                "top_k": 5,
            })
            similar_cases = []
            if hasattr(case_result, "similar_cases"):
                for c in case_result.similar_cases:
                    similar_cases.append(
                        {"content": c.get("content", ""), "metadata": c.get("metadata", {})}
                        if isinstance(c, dict)
                        else {"content": str(c), "metadata": {}}
                    )
            elif isinstance(case_result, dict):
                for c in case_result.get("similar_cases", []):
                    similar_cases.append(
                        {"content": c.get("content", ""), "metadata": c.get("metadata", {})}
                        if isinstance(c, dict)
                        else {"content": str(c), "metadata": {}}
                    )
            else:
                similar_cases = []
        else:
            similar_cases = []
    except Exception as e:
        logger.warning("R2 유사 사례 검색 실패: %s", e)
        similar_cases = []

    return {
        "application_requirements": application_requirements,
        "review_criteria": review_criteria,
        "similar_cases": similar_cases,
    }


# ===============================
# Node 3: LLM으로 폼 필드 값 생성
# ===============================

async def generate_draft_node(state: ApplicationDrafterState) -> dict:
    """form_schema를 템플릿으로 사용하여 LLM이 canonical 기반으로 값 생성

    입력: form_schema (트랙별 폼 구조), canonical (서비스 정보)
    출력: application_draft (form_schema와 동일 구조, 값은 canonical 기반 생성)
    """
    canonical = state.get("canonical", {})
    track = state.get("track", "demo")
    track_korean = TRACK_NAME_MAP.get(track, "실증특례")
    form_schema = state.get("form_schema", {})

    application_requirements = state.get("application_requirements", [])
    review_criteria = state.get("review_criteria", [])
    similar_cases = state.get("similar_cases", [])

    service_info = get_service_info(canonical)

    # form_schema를 보기 좋은 JSON으로 직렬화
    form_schema_json = json.dumps(form_schema, ensure_ascii=False, indent=2)

    prompt = DRAFT_USER_PROMPT.format(
        service_info=service_info,
        track=track_korean,
        application_requirements=format_rag_results(application_requirements),
        review_criteria=format_rag_results(review_criteria),
        similar_cases=format_rag_results(similar_cases),
        form_schema_json=form_schema_json,
    )

    llm = get_llm()
    model_name = settings.LLM_MODEL

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])

        raw_text = response.content.strip()

        # JSON 파싱 (코드 블록 제거)
        json_text = raw_text
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        if json_match:
            json_text = json_match.group(1)

        application_draft = json.loads(json_text)

    except json.JSONDecodeError as e:
        logger.error("LLM 응답 JSON 파싱 실패: %s", e)
        # 파싱 실패 시 빈 폼 스키마 그대로 반환
        application_draft = form_schema
    except Exception as e:
        logger.error("LLM 호출 실패: %s", e)
        application_draft = form_schema

    return {
        "application_draft": application_draft,
        "model_name": model_name,
    }
