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

from app.agents.application_drafter.form_schema import load_form_schema, validate_schema_keys
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
    search_domain_law,
)

logger = logging.getLogger(__name__)


# ============================================================================
# PII 마스킹 함수 (외부 LLM 전송 시 개인정보 보호)
# ============================================================================

def mask_name(name: str) -> str:
    """이름 마스킹: 첫 글자만 표시 (김영희 → 김**)"""
    if not name or len(name) < 2:
        return "[REDACTED]"
    return name[0] + "*" * (len(name) - 1)


def mask_business_number(number: str) -> str:
    """사업자등록번호 마스킹: 마지막 4자리만 표시 (123-45-67890 → ***-**-*7890)"""
    if not number:
        return "[REDACTED]"
    digits_only = re.sub(r"[^0-9]", "", number)
    if len(digits_only) < 4:
        return "[REDACTED]"
    return f"***-**-*{digits_only[-4:]}"


def mask_phone(phone: str) -> str:
    """전화번호 마스킹: 마지막 4자리만 표시 (010-1234-5678 → ***-****-5678)"""
    if not phone:
        return "[REDACTED]"
    digits_only = re.sub(r"[^0-9]", "", phone)
    if len(digits_only) < 4:
        return "[REDACTED]"
    return f"***-****-{digits_only[-4:]}"


def mask_email(email: str) -> str:
    """이메일 마스킹: 도메인만 표시 (user@example.com → ***@example.com)"""
    if not email or "@" not in email:
        return "[REDACTED]"
    _, domain = email.split("@", 1)
    return f"***@{domain}"


def mask_address(address: str) -> str:
    """주소 마스킹: 시/도까지만 표시 (서울특별시 강남구 ... → 서울특별시 [상세주소 생략])"""
    if not address:
        return "[REDACTED]"
    # 시/도 패턴 추출
    match = re.match(r"^(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|강원도|충청북도|충청남도|전라북도|전라남도|경상북도|경상남도|제주특별자치도|[가-힣]+시|[가-힣]+도)", address)
    if match:
        return f"{match.group(1)} [상세주소 생략]"
    return "[REDACTED]"


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY,
    )


def get_service_info(canonical: dict) -> str:
    """canonical에서 서비스 정보 텍스트 추출

    Note: 외부 LLM(OpenAI) 전송 시 PII 보호를 위해 민감 정보는 마스킹 처리됩니다.
    실제 값은 클라이언트에서 폼 기본값으로 별도 처리합니다.
    """
    parts = []

    company = canonical.get("company", {})
    # 회사명은 초안 생성에 필요하므로 유지
    if company.get("company_name"):
        parts.append(f"회사명: {company['company_name']}")
    # PII 필드는 마스킹 처리
    if company.get("representative"):
        parts.append(f"대표자: {mask_name(company['representative'])}")
    if company.get("business_number"):
        parts.append(f"사업자등록번호: {mask_business_number(company['business_number'])}")
    if company.get("address"):
        parts.append(f"주소: {mask_address(company['address'])}")
    if company.get("contact"):
        parts.append(f"전화번호: {mask_phone(company['contact'])}")
    if company.get("email"):
        parts.append(f"이메일: {mask_email(company['email'])}")

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

            def _case_to_dict(c) -> dict:
                """CaseResult 객체 또는 dict를 표준 dict로 변환"""
                # CaseResult Pydantic 모델인 경우
                if hasattr(c, "service_name") and hasattr(c, "company_name"):
                    return {
                        "case_id": getattr(c, "case_id", ""),
                        "company_name": getattr(c, "company_name", ""),
                        "service_name": getattr(c, "service_name", ""),
                        "track": getattr(c, "track", ""),
                        "service_description": getattr(c, "service_description", ""),
                        "current_regulation": getattr(c, "current_regulation", ""),
                        "special_provisions": getattr(c, "special_provisions", ""),
                        "conditions": getattr(c, "conditions", []),
                        "pilot_scope": getattr(c, "pilot_scope", ""),
                        "expected_effect": getattr(c, "expected_effect", ""),
                        "review_result": getattr(c, "review_result", ""),
                    }
                # dict인 경우
                elif isinstance(c, dict):
                    return {
                        "content": c.get("content", c.get("service_description", "")),
                        "metadata": c.get("metadata", {}),
                        **{k: v for k, v in c.items() if k not in ("content", "metadata")},
                    }
                # 기타 (fallback)
                else:
                    return {"content": str(c), "metadata": {}}

            if hasattr(case_result, "similar_cases"):
                similar_cases = [_case_to_dict(c) for c in case_result.similar_cases]
            elif isinstance(case_result, dict):
                similar_cases = [_case_to_dict(c) for c in case_result.get("similar_cases", [])]
            else:
                similar_cases = []
        else:
            similar_cases = []
    except Exception as e:
        logger.warning("R2 유사 사례 검색 실패: %s", e)
        similar_cases = []

    # R3: 도메인별 규제/법령 (근거 문장용)
    try:
        if service_desc:
            law_result = search_domain_law.invoke({
                "query": service_desc,
                "top_k": 5,
            })
            domain_laws = []
            if hasattr(law_result, "results"):
                for r in law_result.results:
                    domain_laws.append({
                        "content": r.content if hasattr(r, "content") else str(r),
                        "metadata": {
                            "law_name": getattr(r, "law_name", ""),
                            "article": getattr(r, "article", ""),
                        }
                    })
            elif isinstance(law_result, dict):
                for r in law_result.get("results", []):
                    domain_laws.append({
                        "content": r.get("content", str(r)),
                        "metadata": r.get("metadata", {}),
                    })
            else:
                domain_laws = []
        else:
            domain_laws = []
    except Exception as e:
        logger.warning("R3 도메인 법령 검색 실패: %s", e)
        domain_laws = []

    return {
        "application_requirements": application_requirements,
        "review_criteria": review_criteria,
        "similar_cases": similar_cases,
        "domain_laws": domain_laws,
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
    domain_laws = state.get("domain_laws", [])

    service_info = get_service_info(canonical)

    # form_schema를 보기 좋은 JSON으로 직렬화
    form_schema_json = json.dumps(form_schema, ensure_ascii=False, indent=2)

    prompt = DRAFT_USER_PROMPT.format(
        service_info=service_info,
        track=track_korean,
        application_requirements=format_rag_results(application_requirements),
        review_criteria=format_rag_results(review_criteria),
        similar_cases=format_rag_results(similar_cases),
        domain_laws=format_rag_results(domain_laws),
        form_schema_json=form_schema_json,
    )

    llm = get_llm()
    model_name = settings.LLM_MODEL

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])

        # 응답 유효성 검사
        if not response.content:
            logger.error("LLM 응답이 비어있습니다")
            application_draft = form_schema
            return {
                "application_draft": application_draft,
                "model_name": model_name,
            }

        raw_text = response.content.strip()

        # JSON 파싱 (코드 블록 제거)
        json_text = raw_text
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        if json_match:
            json_text = json_match.group(1)

        if not json_text:
            logger.error("JSON 텍스트가 비어있습니다")
            application_draft = form_schema
            return {
                "application_draft": application_draft,
                "model_name": model_name,
            }

        application_draft = json.loads(json_text)

        # 스키마 검증: LLM이 잘못된 경로를 만들었는지 확인
        validation = validate_schema_keys(application_draft, form_schema)
        if not validation["valid"]:
            logger.error(
                "LLM이 스키마에 없는 키를 생성함: %s",
                validation["unknown_keys"][:5]
            )
            # 잘못된 키가 있어도 일단 반환 (MVP: 로깅만, 추후 에러 처리 강화)

        if validation["missing_keys"]:
            logger.info(
                "생성되지 않은 필드: %d개 (정상일 수 있음)",
                len(validation["missing_keys"])
            )

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
