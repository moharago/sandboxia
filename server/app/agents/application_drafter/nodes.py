"""Application Drafter Agent 노드 함수

접근 방식:
- 트랙에 맞는 폼 스키마를 서버에서 로드
- canonical 데이터를 기반으로 LLM이 폼 필드 값 생성
- 결과를 application_draft로 저장
"""

import copy
import json
import logging
import re
import time
from datetime import date

from langchain_openai import ChatOpenAI

from app.agents.application_drafter.form_schema import load_form_schema
from app.agents.application_drafter.prompts import (
    ADDITIONAL_QUESTIONS_PROMPT,
    EMPTY_FIELDS_SYSTEM_PROMPT,
    EMPTY_FIELDS_USER_PROMPT,
    REGULATORY_EXEMPTION_REASON_PROMPT,
    TEMPORARY_PERMIT_REASON_PROMPT,
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
# 트랙별 section_texts → 폼 필드 매핑 테이블
# ============================================================================

# section_texts 키 → (form_id, section_key, field_key) 매핑
# 트랙별로 다른 폼 구조에 맞게 매핑
SECTION_TEXT_MAPPING = {
    # 신속확인 (quick_check) 폼 매핑
    "quick_check": {
        "technologyServiceDetails": [("fastcheck-1", "technologyServiceDetails", "technologyServiceDetails")],
        "legalIssues": [("fastcheck-1", "legalIssues", "legalIssues")],
        "additionalQuestions": [("fastcheck-1", "additionalQuestions", "additionalQuestions")],
        # 임시/실증에서 오는 경우 변환
        "detailedDescription": [("fastcheck-1", "technologyServiceDetails", "technologyServiceDetails")],
        "regulationDetails": [("fastcheck-1", "legalIssues", "legalIssues")],
        "necessityAndRequest": [("fastcheck-1", "additionalQuestions", "additionalQuestions")],
    },
    # 임시허가 (temp_permit) 폼 매핑
    "temp_permit": {
        "detailedDescription": [("temporary-2", "technologyService", "detailedDescription")],
        "marketStatusAndOutlook": [("temporary-2", "technologyService", "marketStatusAndOutlook")],
        "regulationDetails": [("temporary-2", "temporaryPermitRequest", "regulationDetails")],
        "necessityAndRequest": [("temporary-2", "temporaryPermitRequest", "necessityAndRequest")],
        "objectivesAndScope": [("temporary-2", "businessPlan", "objectivesAndScope")],
        "businessContent": [("temporary-2", "businessPlan", "businessContent")],
        "schedule": [("temporary-2", "businessPlan", "schedule")],
        "operationPlan": [("temporary-2", "operationPlan", "operationPlan")],
        "quantitativeEffect": [("temporary-2", "expectedEffects", "quantitative")],
        "qualitativeEffect": [("temporary-2", "expectedEffects", "qualitative")],
        "expansionPlan": [("temporary-2", "expansionPlan", "expansionPlan")],
        "organizationStructure": [("temporary-2", "organizationAndBudget", "organizationStructure")],
        "budget": [("temporary-2", "organizationAndBudget", "budget")],
        "mainBusiness": [("temporary-2", "organizationProfile", "mainBusiness")],
        "licensesAndPermits": [("temporary-2", "organizationProfile", "licensesAndPermits")],
        "technologiesAndPatents": [("temporary-2", "organizationProfile", "technologiesAndPatents")],
        "safetyVerification": [("temporary-4", "safetyVerification", "safetyVerification")],
        "userProtectionPlan": [("temporary-4", "userProtectionPlan", "userProtectionPlan")],
        "riskAndResponse": [("temporary-4", "riskAndResponse", "riskAndResponse")],
        "stakeholderConflictResolution": [("temporary-4", "stakeholderConflictResolution", "stakeholderConflictResolution")],
        "justification": [("temporary-3", "justification", "justification")],
        # 신속확인에서 오는 경우 변환
        "technologyServiceDetails": [("temporary-2", "technologyService", "detailedDescription")],
        "legalIssues": [("temporary-2", "temporaryPermitRequest", "regulationDetails")],
    },
    # 실증특례 (demo) 폼 매핑
    "demo": {
        "detailedDescription": [("demonstration-2", "technologyService", "detailedDescription")],
        "marketStatusAndOutlook": [("demonstration-2", "technologyService", "marketStatusAndOutlook")],
        "regulationDetails": [("demonstration-2", "regulatoryExemption", "regulationDetails")],
        "necessityAndRequest": [("demonstration-2", "regulatoryExemption", "necessityAndRequest")],
        "objectivesAndScope": [("demonstration-2", "testPlan", "objectivesAndScope")],
        "executionMethod": [("demonstration-2", "testPlan", "executionMethod")],
        "businessContent": [("demonstration-2", "testPlan", "executionMethod")],
        "schedule": [("demonstration-2", "testPlan", "schedule")],
        "operationPlan": [("demonstration-2", "operationPlan", "operationPlan")],
        "quantitativeEffect": [("demonstration-2", "expectedEffects", "quantitative")],
        "qualitativeEffect": [("demonstration-2", "expectedEffects", "qualitative")],
        "expansionPlan": [("demonstration-2", "postTestPlan", "expansionPlan")],
        "restorationPlan": [("demonstration-2", "postTestPlan", "restorationPlan")],
        "organizationStructure": [("demonstration-2", "organizationAndBudget", "organizationStructure")],
        "budget": [("demonstration-2", "organizationAndBudget", "budget")],
        "mainBusiness": [("demonstration-2", "organizationProfile", "mainBusiness")],
        "licensesAndPermits": [("demonstration-2", "organizationProfile", "licensesAndPermits")],
        "technologiesAndPatents": [("demonstration-2", "organizationProfile", "technologiesAndPatents")],
        "safetyVerification": [("demonstration-4", "safetyVerification", "safetyVerification")],
        "userProtectionPlan": [("demonstration-4", "userProtectionPlan", "userProtectionPlan")],
        "protectionAndResponse": [("demonstration-4", "protectionAndResponse", "protectionAndResponse")],
        "riskAndMitigation": [("demonstration-4", "riskAndMitigation", "riskAndMitigation")],
        "riskAndResponse": [("demonstration-4", "riskAndMitigation", "riskAndMitigation")],
        "stakeholderConflict": [("demonstration-4", "stakeholderConflict", "stakeholderConflict")],
        "stakeholderConflictResolution": [("demonstration-4", "stakeholderConflict", "stakeholderConflict")],
        "justification": [("demonstration-3", "justification", "justification")],
        # 신속확인에서 오는 경우 변환
        "technologyServiceDetails": [("demonstration-2", "technologyService", "detailedDescription")],
        "legalIssues": [("demonstration-2", "regulatoryExemption", "regulationDetails")],
    },
}

# 서술형 필드 목록 (LLM 생성 대상)
DESCRIPTIVE_FIELDS = {
    "detailedDescription", "marketStatusAndOutlook", "regulationDetails",
    "necessityAndRequest", "objectivesAndScope", "businessContent",
    "executionMethod", "schedule", "operationPlan", "quantitative",
    "qualitative", "expansionPlan", "restorationPlan", "organizationStructure",
    "budget", "safetyVerification", "userProtectionPlan", "riskAndResponse",
    "riskAndMitigation", "protectionAndResponse", "stakeholderConflictResolution",
    "stakeholderConflict", "justification", "mainBusiness", "licensesAndPermits",
    "technologiesAndPatents", "technologyServiceDetails", "legalIssues",
    "additionalQuestions",
}

# 숫자/금액 등 사실 정보 포함 필드 - LLM이 빈 값일 때 생성하지 않음 (할루시네이션 방지)
# section_texts에서 추출된 경우에만 값을 사용하고, 없으면 빈 상태로 유지
NO_LLM_GENERATE_FIELDS = {
    "budget",           # 예산 (금액 할루시네이션 방지)
    "quantitative",     # 정량적 효과 (수치 할루시네이션 방지)
}


# HWP 템플릿의 플레이스홀더/가이드 텍스트 목록
# 이 텍스트들은 실제 내용이 아니므로 빈 값으로 취급
PLACEHOLDER_TEXTS = {
    "작성 방법",
    "작성방법",
    "작성 예시",
    "작성예시",
    "(작성 방법)",
    "(작성방법)",
    "[작성 방법]",
    "[작성방법]",
    "내용을 입력하세요",
    "내용 입력",
    "여기에 입력",
    "예시",
    "예:",
    "ex)",
    "ex:",
}


def _is_placeholder_text(text: str) -> bool:
    """플레이스홀더/가이드 텍스트인지 확인"""
    if not text:
        return True
    text_stripped = text.strip()
    # 정확히 일치하는 경우
    if text_stripped in PLACEHOLDER_TEXTS:
        return True
    # "작성 방법"으로 시작하는 짧은 텍스트 (예: "작성 방법\n")
    if text_stripped.startswith("작성") and len(text_stripped) < 20:
        return True
    return False


def _prefill_from_section_texts(draft: dict, canonical: dict, target_track: str) -> dict:
    """section_texts에서 폼 필드로 직접 매핑 (LLM 호출 없이)

    같은 트랙이든 다른 트랙이든, section_texts에 내용이 있으면 그대로 복사합니다.
    트랙별 매핑 테이블을 사용하여 올바른 폼 필드에 배치합니다.
    플레이스홀더 텍스트(예: "작성 방법")는 건너뜁니다.
    """
    section_texts = canonical.get("section_texts", {})
    if not section_texts:
        return draft

    mapping = SECTION_TEXT_MAPPING.get(target_track, {})
    if not mapping:
        logger.warning("Unknown target track for mapping: %s", target_track)
        return draft

    filled_count = 0
    skipped_count = 0
    for section_key, raw_text in section_texts.items():
        if not raw_text:  # null이면 건너뜀
            continue

        # 플레이스홀더 텍스트는 건너뜀 (LLM이 생성하도록)
        if _is_placeholder_text(raw_text):
            skipped_count += 1
            logger.debug("[PREFILL] 플레이스홀더 텍스트 건너뜀: %s = '%s'", section_key, raw_text[:30])
            continue

        targets = mapping.get(section_key)
        if not targets:
            # 매핑이 없는 키는 무시 (다른 트랙 전용 필드일 수 있음)
            continue

        for form_id, section_name, field_name in targets:
            if form_id not in draft:
                continue

            form_data = draft[form_id]
            if "data" in form_data:
                form_data = form_data["data"]

            if section_name not in form_data:
                form_data[section_name] = {}

            # 원문 그대로 복사
            form_data[section_name][field_name] = raw_text
            filled_count += 1

    logger.info("[PREFILL] section_texts에서 %d개 필드 직접 매핑, %d개 플레이스홀더 건너뜀", filled_count, skipped_count)
    return draft


def _get_empty_descriptive_fields(draft: dict) -> list[dict]:
    """채워지지 않은 서술형 필드 목록 반환

    플레이스홀더 텍스트(예: "작성 방법")도 빈 값으로 취급합니다.

    Returns:
        list of {"form_id": str, "section": str, "field": str}
    """
    empty_fields = []

    for form_id, form_content in draft.items():
        if not isinstance(form_content, dict):
            continue

        # data 키가 있으면 그 안을 확인
        data = form_content.get("data", form_content)
        if not isinstance(data, dict):
            continue

        for section_key, section_data in data.items():
            if not isinstance(section_data, dict):
                continue
            if section_key in ("formId", "formName", "version", "sections"):
                continue

            for field_key, field_value in section_data.items():
                # 숫자/금액 필드는 LLM 생성 대상에서 제외 (할루시네이션 방지)
                if field_key in NO_LLM_GENERATE_FIELDS:
                    continue

                # 서술형 필드이고 비어있거나 플레이스홀더인 경우
                if field_key in DESCRIPTIVE_FIELDS:
                    is_empty = (
                        not field_value
                        or field_value == ""
                        or field_value is None
                        or _is_placeholder_text(str(field_value))
                    )
                    if is_empty:
                        empty_fields.append({
                            "form_id": form_id,
                            "section": section_key,
                            "field": field_key,
                        })

    return empty_fields


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
        max_tokens=8000,  # 텍스트 잘림 방지
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
            # 정식 표현 (HWP 파서에서 추출)
            "기술인 경우": "technology",
            "기술인경우": "technology",
            "서비스인 경우": "service",
            "서비스인경우": "service",
            "기술과 서비스가 융합된 경우": "technologyAndService",
            "기술과서비스가융합된경우": "technologyAndService",
            # 단축 표현 (HWP 체크박스 라벨에서 추출된 경우)
            "기술": "technology",
            "서비스": "service",
            "기술과서비스": "technologyAndService",
            "기술과 서비스": "technologyAndService",
            "기술서비스": "technologyAndService",
            "융합": "technologyAndService",
        }
        # 공백 제거 후 매핑
        service_type_normalized = service_type_raw.replace(" ", "")
        service_type_value = service_type_map.get(service_type_normalized) or service_type_map.get(service_type_raw, service_type_raw)
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


def get_section_texts_info(canonical: dict) -> str:
    """canonical에서 section_texts 정보를 텍스트로 추출

    HWP에서 파싱된 섹션별 원문을 LLM에 전달하여
    내용을 보존하면서 다듬어서 작성하도록 합니다.
    """
    section_texts = canonical.get("section_texts", {})
    if not section_texts:
        return "섹션별 원문 없음"

    # 섹션 키 → 한글 라벨 매핑
    SECTION_LABELS = {
        "detailedDescription": "기술·서비스 세부 내용",
        "technologyServiceDetails": "기술·서비스 세부 내용 (신속확인용)",
        "marketStatusAndOutlook": "시장 현황 및 전망",
        "regulationDetails": "규제 내용",
        "legalIssues": "법·제도 이슈 사항 (신속확인용)",
        "necessityAndRequest": "임시허가/규제특례 필요성 및 내용",
        "objectivesAndScope": "사업/실증 목표 및 범위",
        "businessContent": "사업 내용",
        "schedule": "사업/실증 기간 및 일정 계획",
        "operationPlan": "사업/실증 운영 계획",
        "quantitativeEffect": "정량적 기대효과",
        "qualitativeEffect": "정성적 기대효과",
        "expansionPlan": "사업 확대·확산 계획",
        "organizationStructure": "추진 체계",
        "budget": "추진 예산",
        "safetyVerification": "안전성 검증 자료",
        "userProtectionPlan": "이용자 보호 및 대응 계획",
        "riskAndResponse": "위험 및 대응 방안",
        "stakeholderConflictResolution": "이해관계 충돌 해소 방안",
        "justification": "해당여부에 대한 근거",
        "additionalQuestions": "기타 질의 사항 (신속확인용)",
        "mainBusiness": "주요 사업",
        "licensesAndPermits": "주요 인허가 사항",
        "technologiesAndPatents": "보유기술 및 특허",
    }

    parts = []
    for key, raw_text in section_texts.items():
        if raw_text:  # null이 아닌 경우만
            label = SECTION_LABELS.get(key, key)
            parts.append(f"### {label}\n{raw_text}")

    return "\n\n".join(parts) if parts else "섹션별 원문 없음"


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
    start_time = time.time()
    track = state.get("track", "demo")

    try:
        form_schema = load_form_schema(track)
        logger.info("폼 스키마 로드 완료: track=%s, forms=%d", track, len(form_schema))
    except (ValueError, FileNotFoundError) as e:
        logger.error("폼 스키마 로드 실패: %s", e)
        form_schema = {}

    elapsed = time.time() - start_time
    print(f"[Step4] 폼 스키마 로드 완료 ({elapsed:.2f}초)")

    return {"form_schema": form_schema}


# ===============================
# Node 2: RAG 컨텍스트 검색
# ===============================

async def retrieve_context_node(state: ApplicationDrafterState) -> dict:
    """R1/R2 RAG 검색으로 신청서 작성에 필요한 컨텍스트 수집"""
    start_time = time.time()
    canonical = state.get("canonical", {})
    track = state.get("track", "demo")
    track_korean = TRACK_NAME_MAP.get(track, "실증특례")

    service_desc = get_service_description(canonical)

    # R1: 신청 요건/작성 가이드
    try:
        app_req_results = get_application_requirements.invoke({"track": track_korean})
        application_requirements = [r.model_dump() for r in app_req_results]
    except Exception as e:
        logger.warning("R1 신청 요건 검색 실패: %s", e)
        application_requirements = []

    # R1: 심사 기준
    try:
        review_results = get_review_criteria.invoke({"track": track_korean})
        review_criteria = [r.model_dump() for r in review_results]
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
                """CaseResult 객체 또는 dict를 표준 dict로 변환

                format_rag_results 호환을 위해 "content" 키 포함
                """
                # CaseResult Pydantic 모델인 경우
                if hasattr(c, "service_name") and hasattr(c, "company_name"):
                    # 개별 필드 추출
                    case_id = getattr(c, "case_id", "")
                    company_name = getattr(c, "company_name", "")
                    service_name = getattr(c, "service_name", "")
                    track = getattr(c, "track", "")
                    service_description = getattr(c, "service_description", "")
                    current_regulation = getattr(c, "current_regulation", "")
                    special_provisions = getattr(c, "special_provisions", "")
                    conditions = getattr(c, "conditions", [])
                    pilot_scope = getattr(c, "pilot_scope", "")
                    expected_effect = getattr(c, "expected_effect", "")
                    review_result = getattr(c, "review_result", "")
                    designation_date = getattr(c, "designation_date", "")
                    source_url = getattr(c, "source_url", None)

                    # format_rag_results 호환용 content 문자열 생성
                    conditions_str = ", ".join(conditions) if conditions else ""
                    content_parts = [
                        f"[{track}] {service_name} ({company_name})",
                        f"서비스: {service_description}" if service_description else "",
                        f"현행규제: {current_regulation}" if current_regulation else "",
                        f"특례내용: {special_provisions}" if special_provisions else "",
                        f"실증범위: {pilot_scope}" if pilot_scope else "",
                        f"조건: {conditions_str}" if conditions_str else "",
                        f"기대효과: {expected_effect}" if expected_effect else "",
                        f"심의결과: {review_result}" if review_result else "",
                    ]
                    content = "\n".join(part for part in content_parts if part)

                    return {
                        "content": content,
                        "case_id": case_id,
                        "company_name": company_name,
                        "service_name": service_name,
                        "track": track,
                        "service_description": service_description,
                        "current_regulation": current_regulation,
                        "special_provisions": special_provisions,
                        "conditions": conditions,
                        "pilot_scope": pilot_scope,
                        "expected_effect": expected_effect,
                        "review_result": review_result,
                        "designation_date": designation_date,
                        "source_url": source_url,
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
                            "citation": getattr(r, "citation", ""),
                            "domain_label": getattr(r, "domain_label", ""),
                            "source_url": getattr(r, "source_url", None),
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

    # DEBUG: RAG 검색 결과 출력
    print("\n" + "=" * 60)
    print("[DEBUG] RAG 검색 결과")
    print("=" * 60)

    print(f"\n[R1] 신청 요건 ({len(application_requirements)}건):")
    for i, req in enumerate(application_requirements, 1):
        content = req.get("content", str(req))[:200]
        print(f"  {i}. {content}...")

    print(f"\n[R1] 심사 기준 ({len(review_criteria)}건):")
    for i, crit in enumerate(review_criteria, 1):
        content = crit.get("content", str(crit))[:200]
        print(f"  {i}. {content}...")

    print(f"\n[R2] 유사 승인 사례 ({len(similar_cases)}건):")
    for i, case in enumerate(similar_cases, 1):
        content = case.get("content", str(case))[:200]
        print(f"  {i}. {content}...")

    print(f"\n[R3] 도메인 법령 ({len(domain_laws)}건):")
    for i, law in enumerate(domain_laws, 1):
        content = law.get("content", str(law))[:200]
        metadata = law.get("metadata", {})
        law_name = metadata.get("law_name", "")
        print(f"  {i}. [{law_name}] {content}...")

    print("=" * 60 + "\n")

    elapsed = time.time() - start_time
    print(f"[Step4] RAG 컨텍스트 검색 완료 ({elapsed:.2f}초)")

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
    """form_schema를 기반으로 초안 생성

    새로운 효율적 접근 방식:
    1. form_schema 복사 → 빈 드래프트 생성
    2. pass-through 데이터 채움 (회사정보, 재무현황 등)
    3. section_texts에서 직접 매핑 (LLM 없이)
    4. 비어있는 서술형 필드만 LLM에게 생성 요청
    """
    start_time = time.time()
    canonical = state.get("canonical", {})
    track = state.get("track", "demo")
    form_schema = state.get("form_schema", {})

    application_requirements = state.get("application_requirements", [])
    review_criteria = state.get("review_criteria", [])
    similar_cases = state.get("similar_cases", [])
    domain_laws = state.get("domain_laws", [])

    model_name = settings.LLM_MODEL

    # ==============================
    # Step 1: 폼 스키마 복사
    # ==============================
    application_draft = copy.deepcopy(form_schema)
    logger.info("[DRAFT] Step 1: 폼 스키마 복사 완료")

    # ==============================
    # Step 2: Pass-through 데이터 먼저 채움
    # 회사정보, 재무현황 등 canonical에서 그대로 복사
    # ==============================
    application_draft = _merge_passthrough_data(application_draft, canonical, track)
    logger.info("[DRAFT] Step 2: Pass-through 데이터 채움 완료")

    # ==============================
    # Step 3: section_texts에서 직접 매핑 (LLM 없이)
    # 같은 트랙이든 다른 트랙이든, 원문이 있으면 그대로 복사
    # ==============================
    application_draft = _prefill_from_section_texts(application_draft, canonical, track)
    logger.info("[DRAFT] Step 3: section_texts 직접 매핑 완료")

    # ==============================
    # Step 3.5: 트랙 변환 시 필드 초기화 (LLM이 재생성하도록)
    # 임시허가 ↔ 실증특례 변환 시, 용어/구조가 다른 필드들을 비움
    # 이렇게 해야 Step 4에서 LLM이 해당 필드들을 새로 생성함
    # ==============================
    application_draft = _convert_temp_demo_reason(application_draft, canonical, track)
    logger.info("[DRAFT] Step 3.5: 트랙 변환 처리 완료")

    # ==============================
    # Step 4: 비어있는 서술형 필드만 LLM에게 생성 요청
    # ==============================
    empty_fields = _get_empty_descriptive_fields(application_draft)

    print("\n" + "=" * 60)
    print(f"[DEBUG] 빈 서술형 필드: {len(empty_fields)}개")
    for ef in empty_fields[:10]:  # 처음 10개만 출력
        print(f"  - {ef['form_id']}.{ef['section']}.{ef['field']}")
    if len(empty_fields) > 10:
        print(f"  ... 외 {len(empty_fields) - 10}개")
    print("=" * 60 + "\n")

    if empty_fields:
        logger.info("[DRAFT] Step 4: %d개 빈 필드 LLM 생성 시작", len(empty_fields))

        # 빈 필드 목록을 JSON으로 변환
        empty_fields_json = json.dumps(
            [f"{ef['form_id']}.{ef['section']}.{ef['field']}" for ef in empty_fields],
            ensure_ascii=False,
            indent=2
        )

        service_info = get_service_info(canonical)

        prompt = EMPTY_FIELDS_USER_PROMPT.format(
            service_info=service_info,
            application_requirements=format_rag_results(application_requirements),
            review_criteria=format_rag_results(review_criteria),
            similar_cases=format_rag_results(similar_cases),
            domain_laws=format_rag_results(domain_laws),
            empty_fields_json=empty_fields_json,
        )

        llm = get_llm()

        try:
            response = await llm.ainvoke([
                {"role": "system", "content": EMPTY_FIELDS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])

            if response.content:
                raw_text = response.content.strip()

                # JSON 파싱
                json_text = raw_text
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
                if json_match:
                    json_text = json_match.group(1)

                if json_text:
                    generated_fields = json.loads(json_text)

                    # 생성된 필드를 드래프트에 병합
                    filled_count = 0
                    for field_path, value in generated_fields.items():
                        parts = field_path.split(".")
                        if len(parts) == 3:
                            form_id, section, field = parts
                            if form_id in application_draft:
                                form_data = application_draft[form_id]
                                if "data" in form_data:
                                    form_data = form_data["data"]
                                if section not in form_data:
                                    form_data[section] = {}
                                form_data[section][field] = value
                                form_data[section]["generated_by"] = "ai"
                                filled_count += 1

                    logger.info("[DRAFT] LLM이 %d개 빈 필드 생성 완료", filled_count)

        except json.JSONDecodeError as e:
            logger.error("LLM 응답 JSON 파싱 실패: %s", e)
        except Exception as e:
            logger.error("LLM 빈 필드 생성 실패: %s", e)
    else:
        logger.info("[DRAFT] Step 4: 빈 서술형 필드 없음, LLM 호출 스킵")

    # ==============================
    # Step 5: 트랙 변환 시 추가 처리
    # ==============================
    # 임시허가/실증특례 → 신속확인: additionalQuestions
    application_draft = await _generate_additional_questions(
        application_draft, canonical, track
    )
    # 신속확인 → 실증특례: regulatoryExemptionReason
    application_draft = await _generate_regulatory_exemption_reason(
        application_draft, canonical, track
    )
    # 신속확인 → 임시허가: temporaryPermitReason
    application_draft = await _generate_temporary_permit_reason(
        application_draft, canonical, track
    )
    # NOTE: _convert_temp_demo_reason은 Step 3.5에서 이미 호출됨 (LLM 생성 전에 필드 초기화 필요)

    elapsed = time.time() - start_time
    print(f"[Step4] 초안 생성 (LLM 포함) 완료 ({elapsed:.2f}초)")

    logger.info("[DRAFT] 초안 생성 완료")

    return {
        "application_draft": application_draft,
        "model_name": model_name,
    }


def _get_form_data(draft: dict, form_id: str) -> dict | None:
    """폼의 data 섹션을 가져오거나 생성합니다.

    폼 스키마 구조: {form_id: {formId: ..., data: {...}}}

    Returns:
        form_id가 없으면 None, 있으면 data dict 참조 반환
    """
    if form_id not in draft:
        return None
    if "data" not in draft[form_id]:
        draft[form_id]["data"] = {}
    return draft[form_id]["data"]


def _merge_passthrough_data(draft: dict, canonical: dict, target_track: str) -> dict:
    """canonical의 재무현황/인력현황/사업계획/신청기관 데이터를 draft에 병합

    AI가 생성하지 않는 숫자/사실 데이터는 canonical에서 그대로 복사합니다.
    데이터가 없으면 (null) 해당 필드는 그대로 유지됩니다.

    주의: LLM 출력 구조는 {form_id: {formId: ..., data: {...}}}이므로
    모든 필드는 data 섹션 안에 추가해야 합니다.
    """
    # DEBUG: canonical 데이터 확인
    logger.info("[DEBUG] canonical keys: %s", list(canonical.keys()))
    logger.info("[DEBUG] canonical.project_plan: %s", canonical.get("project_plan"))
    logger.info("[DEBUG] canonical.applicants: %s", canonical.get("applicants"))

    # ==============================
    # 서비스 정보 (service) pass-through
    # canonical.service → form.technologyService 매핑
    # ==============================
    service = canonical.get("service", {})
    if service:
        logger.info("[DEBUG] Processing service pass-through: %s", service)

        # service_type 변환 (HWP 한글 → 폼 value)
        service_type_raw = service.get("service_type", "")
        service_type_map = {
            # 정식 표현 (HWP 파서에서 추출)
            "기술인 경우": "technology",
            "기술인경우": "technology",
            "서비스인 경우": "service",
            "서비스인경우": "service",
            "기술과 서비스가 융합된 경우": "technologyAndService",
            "기술과서비스가융합된경우": "technologyAndService",
            # 단축 표현 (HWP 체크박스 라벨에서 추출된 경우)
            "기술": "technology",
            "서비스": "service",
            "기술과서비스": "technologyAndService",
            "기술과 서비스": "technologyAndService",
            "기술서비스": "technologyAndService",
            "융합": "technologyAndService",
        }
        service_type_normalized = service_type_raw.replace(" ", "") if service_type_raw else ""
        service_type_value = service_type_map.get(service_type_normalized) or service_type_map.get(service_type_raw, service_type_raw)

        # technologyService 데이터 구성
        tech_service_data = {}
        if service.get("service_name"):
            tech_service_data["name"] = service["service_name"]
        if service_type_value:
            tech_service_data["type"] = service_type_value
        # mainContent: -1 폼(신청서)은 service_description 사용 (신청서 HWP 원본)
        if service.get("service_description"):
            tech_service_data["mainContent"] = service["service_description"]
            logger.info("[DEBUG] mainContent from service_description for -1 forms")

        if tech_service_data:
            # 모든 -1 폼의 technologyService 섹션에 적용 (신청서)
            for form_id in ["temporary-1", "demonstration-1", "fastcheck-1"]:
                form_data = _get_form_data(draft, form_id)
                if form_data is not None:
                    if "technologyService" not in form_data:
                        form_data["technologyService"] = {}
                    form_data["technologyService"].update(tech_service_data)
                    logger.info("[DEBUG] service pass-through applied to %s: %s", form_id, tech_service_data)

    # ==============================
    # 회사 정보 (company) pass-through - 개인정보 원본값 사용
    # LLM 출력은 마스킹된 값이므로, canonical 원본으로 덮어씀
    # ==============================
    company = canonical.get("company", {})
    if company:
        logger.info("[DEBUG] Processing company pass-through: %s", company)

        # canonical.company → form.applicant 매핑
        applicant_data = {}
        if company.get("company_name"):
            applicant_data["companyName"] = company["company_name"]
        if company.get("representative"):
            applicant_data["representativeName"] = company["representative"]
        if company.get("business_number"):
            applicant_data["businessRegistrationNumber"] = company["business_number"]
        if company.get("address"):
            applicant_data["address"] = company["address"]
        if company.get("contact"):
            applicant_data["phoneNumber"] = company["contact"]
        if company.get("email"):
            applicant_data["email"] = company["email"]

        if applicant_data:
            # 모든 폼의 applicant 섹션에 원본 데이터 적용
            for form_id in ["temporary-1", "demonstration-1", "fastcheck-1", "counseling-1"]:
                form_data = _get_form_data(draft, form_id)
                if form_data is not None:
                    if "applicant" not in form_data:
                        form_data["applicant"] = {}
                    form_data["applicant"].update(applicant_data)
                    logger.info("[DEBUG] company pass-through applied to %s", form_id)

        # 사업계획서의 organizationProfile.generalInfo에도 원본 데이터 적용
        # (LLM이 마스킹된 값으로 생성할 수 있으므로 canonical 원본으로 항상 덮어씀)
        for form_id in ["temporary-2", "demonstration-2"]:
            form_data = _get_form_data(draft, form_id)
            if form_data is not None:
                if "organizationProfile" not in form_data:
                    form_data["organizationProfile"] = {}
                org_profile = form_data["organizationProfile"]

                # organizationName = company_name (항상 canonical 값 우선)
                if company.get("company_name"):
                    org_profile["organizationName"] = company["company_name"]

                # generalInfo 섹션
                if "generalInfo" not in org_profile:
                    org_profile["generalInfo"] = {}
                general_info = org_profile["generalInfo"]

                # LLM이 마스킹된 값을 생성할 수 있으므로, canonical에 값이 있으면 항상 덮어씀
                if company.get("representative"):
                    general_info["representativeName"] = company["representative"]
                if company.get("address"):
                    general_info["address"] = company["address"]
                if company.get("establishment_date"):
                    general_info["establishmentDate"] = company["establishment_date"]

                logger.info("[DEBUG] organizationProfile pass-through applied to %s", form_id)

    # ==============================
    # 기관 현황 필드 pass-through (section_texts에서 직접 가져옴)
    # licensesAndPermits, technologiesAndPatents, mainBusiness
    # 문서 기반 생성이므로 fallback 없음 - section_texts에 없으면 빈칸 유지
    # ==============================
    section_texts = canonical.get("section_texts", {})

    for form_id in ["temporary-2", "demonstration-2"]:
        form_data = _get_form_data(draft, form_id)
        if form_data is None:
            continue

        if "organizationProfile" not in form_data:
            form_data["organizationProfile"] = {}
        org_profile = form_data["organizationProfile"]

        # technologiesAndPatents: section_texts 우선, technology fallback
        tech_patents = section_texts.get("technologiesAndPatents")
        if not tech_patents:
            tech_patents = canonical.get("technology", {}).get("technologies_and_patents")
        if tech_patents and not org_profile.get("technologiesAndPatents"):
            org_profile["technologiesAndPatents"] = tech_patents
            logger.info("[DEBUG] technologiesAndPatents applied to %s", form_id)

        # licensesAndPermits: section_texts 우선, company fallback
        licenses = section_texts.get("licensesAndPermits")
        if not licenses:
            licenses = canonical.get("company", {}).get("licenses_and_permits")
        if licenses and not org_profile.get("licensesAndPermits"):
            org_profile["licensesAndPermits"] = licenses
            logger.info("[DEBUG] licensesAndPermits applied to %s", form_id)

        # mainBusiness: section_texts 우선, company.main_business fallback
        main_biz = section_texts.get("mainBusiness")
        if not main_biz:
            # section_texts에 없으면 canonical.company.main_business 사용
            main_biz = canonical.get("company", {}).get("main_business")
        if main_biz and not org_profile.get("mainBusiness"):
            org_profile["mainBusiness"] = main_biz
            logger.info("[DEBUG] mainBusiness applied to %s", form_id)

    # 재무현황 병합 (canonical: year별 구조 → form: row별 구조로 변환)
    # canonical 키 (한글 또는 영문) → form 영문 키 매핑
    FINANCIAL_KEY_MAP = {
        # 한글 키 (HWP 파서 출력)
        "총자산": "totalAssets",
        "자기자본": "equity",
        "유동부채": "currentLiabilities",
        "고정부채": "fixedLiabilities",
        "유동자산": "currentAssets",
        "당기순이익": "netIncome",
        "총매출액": "totalRevenue",
        "자기자본 이익률": "returnOnEquity",
        "부채비율": "debtRatio",
        # 영문 키 (이미 변환된 경우)
        "totalAssets": "totalAssets",
        "equity": "equity",
        "currentLiabilities": "currentLiabilities",
        "fixedLiabilities": "fixedLiabilities",
        "currentAssets": "currentAssets",
        "netIncome": "netIncome",
        "totalRevenue": "totalRevenue",
        "returnOnEquity": "returnOnEquity",
        "debtRatio": "debtRatio",
    }

    financial = canonical.get("financial", {})
    if financial and any(financial.get(year) for year in ["yearM2", "yearM1", "average"]):
        financial_status = {}

        for year in ["yearM2", "yearM1", "average"]:
            year_data = financial.get(year, {})
            if not year_data:
                continue

            for source_key, target_key in FINANCIAL_KEY_MAP.items():
                value = year_data.get(source_key)
                if value is not None:
                    if target_key not in financial_status:
                        financial_status[target_key] = {}
                    financial_status[target_key][year] = value

        logger.info("[DEBUG] financial_status after mapping: %s", financial_status)

        if financial_status:
            for form_id in ["temporary-2", "demonstration-2"]:
                form_data = _get_form_data(draft, form_id)
                if form_data is not None:
                    form_data["financialStatus"] = financial_status

    # 인력현황 병합
    hr = canonical.get("hr", {})
    if hr:
        hr_data = {}
        if hr.get("organizationChart"):
            hr_data["organizationChart"] = hr["organizationChart"]
        if hr.get("totalEmployees"):
            hr_data["totalEmployees"] = hr["totalEmployees"]

        key_personnel = hr.get("keyPersonnel", [])
        if key_personnel and isinstance(key_personnel, list):
            # canonical 필드명 → 클라이언트 필드명 변환
            # qualifications → qualificationsOrSkills
            # experience → experienceYears
            valid_personnel = []
            for p in key_personnel:
                if isinstance(p, dict) and p.get("name"):
                    transformed = {
                        "name": p.get("name", ""),
                        "department": p.get("department", ""),
                        "position": p.get("position", ""),
                        "responsibilities": p.get("responsibilities", ""),
                        "qualificationsOrSkills": p.get("qualifications", ""),
                        "experienceYears": p.get("experience", ""),
                    }
                    valid_personnel.append(transformed)
            if valid_personnel:
                hr_data["keyPersonnel"] = valid_personnel

        if hr_data:
            for form_id in ["temporary-2", "demonstration-2"]:
                form_data = _get_form_data(draft, form_id)
                if form_data is not None:
                    if "humanResources" not in form_data:
                        form_data["humanResources"] = {}
                    form_data["humanResources"].update(
                        {k: v for k, v in hr_data.items() if k != "keyPersonnel"}
                    )
                    if "keyPersonnel" in hr_data:
                        form_data["keyPersonnel"] = hr_data["keyPersonnel"]

    # 사업 계획 (project_plan) 병합
    project_plan = canonical.get("project_plan", {})
    if project_plan:
        logger.info("[DEBUG] Processing project_plan: %s", project_plan)

        for form_id in ["temporary-2", "demonstration-2"]:
            form_data = _get_form_data(draft, form_id)
            if form_data is None:
                continue

            if "projectInfo" not in form_data:
                form_data["projectInfo"] = {}

            if project_plan.get("projectName"):
                form_data["projectInfo"]["projectName"] = project_plan["projectName"]

            if project_plan.get("startDate") or project_plan.get("endDate") or project_plan.get("durationMonths"):
                if "period" not in form_data["projectInfo"]:
                    form_data["projectInfo"]["period"] = {}

                if project_plan.get("startDate"):
                    form_data["projectInfo"]["period"]["startDate"] = project_plan["startDate"]
                if project_plan.get("endDate"):
                    form_data["projectInfo"]["period"]["endDate"] = project_plan["endDate"]
                if project_plan.get("durationMonths"):
                    form_data["projectInfo"]["period"]["durationMonths"] = project_plan["durationMonths"]

            logger.info("[DEBUG] projectInfo set for %s: %s", form_id, form_data["projectInfo"])

    # 신청기관 (applicants) 병합
    applicants = canonical.get("applicants", {})
    logger.info("[DEBUG] Processing applicants: %s", applicants)

    organizations = applicants.get("organizations", []) if applicants else []
    valid_orgs = []

    if organizations and isinstance(organizations, list):
        valid_orgs = [
            {
                "organizationName": org.get("organizationName"),
                "organizationType": org.get("organizationType"),
                "responsiblePersonName": org.get("responsiblePersonName"),
                "position": org.get("position"),
                "phoneNumber": org.get("phoneNumber"),
                "email": org.get("email"),
            }
            for org in organizations
            if isinstance(org, dict) and org.get("organizationName")
        ]

    # organizations가 비어있으면 company 정보로 기본 신청기관 생성
    if not valid_orgs and company:
        default_org = {
            "organizationName": company.get("company_name"),
            "organizationType": "법인",  # 기본값
            "responsiblePersonName": company.get("representative"),
            "position": "대표이사",  # 기본값
            "phoneNumber": company.get("contact"),
            "email": company.get("email"),
        }
        # organizationName이 있어야 유효
        if default_org["organizationName"]:
            valid_orgs = [default_org]
            logger.info("[DEBUG] Created default applicantOrganization from company: %s", default_org)

    if valid_orgs:
        for form_id in ["temporary-2", "demonstration-2"]:
            form_data = _get_form_data(draft, form_id)
            if form_data is not None:
                # LLM이 마스킹된 이름을 생성할 수 있으므로 항상 canonical 값으로 덮어씀
                form_data["applicantOrganizations"] = valid_orgs
                logger.info("[DEBUG] applicantOrganizations overwritten with canonical for %s", form_id)

    if applicants:

        # 제출일자 - HWP에서 파싱된 값 사용, 없으면 오늘 날짜
        # HWP 파서는 snake_case, 일부 데이터는 camelCase 사용 - 둘 다 체크
        submission_date = (
            applicants.get("submission_date") or
            applicants.get("submissionDate") or
            applicants.get("application_date") or
            applicants.get("applicationDate")
        )
        if not submission_date:
            today = date.today()
            submission_date = today.strftime("%Y. %m. %d.")
            logger.info("[DEBUG] submissionDate not found, using today: %s", submission_date)
        else:
            logger.info("[DEBUG] submissionDate from canonical: %s", submission_date)

        for form_id in ["temporary-2", "demonstration-2"]:
            form_data = _get_form_data(draft, form_id)
            if form_data is not None:
                if "submissionDate" not in form_data:
                    form_data["submissionDate"] = {}
                form_data["submissionDate"]["submissionDate"] = submission_date

        # 서명 목록 (LLM이 마스킹된 이름을 생성할 수 있으므로 항상 canonical 값으로 덮어씀)
        # canonical 필드명: signer_name, organization_name
        # 폼 필드명: name, organizationName
        signatures = applicants.get("signatures", [])
        if signatures and isinstance(signatures, list):
            valid_sigs = []
            for sig in signatures:
                if not isinstance(sig, dict):
                    continue
                # canonical 필드명 또는 폼 필드명으로 추출
                name = sig.get("name") or sig.get("signer_name")
                org_name = sig.get("organizationName") or sig.get("organization_name")
                # 플레이스홀더 텍스트 필터링
                if name and "(기관명)" not in name and "(성명)" not in name:
                    valid_sigs.append({
                        "organizationName": org_name or "",
                        "name": name,
                    })
            if valid_sigs:
                for form_id in ["temporary-2", "demonstration-2"]:
                    form_data = _get_form_data(draft, form_id)
                    if form_data is not None:
                        # LLM이 마스킹된 이름을 생성할 수 있으므로 항상 canonical 값으로 덮어씀
                        form_data["submission"] = valid_sigs
                        logger.info("[DEBUG] submission overwritten with canonical signatures for %s", form_id)

    # 신청일자 - HWP에서 파싱된 날짜 사용, 없으면 오늘 날짜
    # HWP 파서는 snake_case, 일부 데이터는 camelCase 사용 - 둘 다 체크
    applicants = canonical.get("applicants", {})
    application_date = (
        applicants.get("application_date") or
        applicants.get("applicationDate")
    ) if applicants else None
    if not application_date:
        today = date.today()
        application_date = today.strftime("%Y. %m. %d.")
        logger.info("[DEBUG] application_date not found, using today: %s", application_date)
    else:
        logger.info("[DEBUG] application_date from HWP: %s", application_date)

    for form_id in ["temporary-1", "demonstration-1", "fastcheck-1"]:
        form_data = _get_form_data(draft, form_id)
        if form_data is not None:
            if "application" not in form_data:
                form_data["application"] = {}
            form_data["application"]["applicationDate"] = application_date

    # 체크박스 선택값 (form_selections) 병합
    form_selections = canonical.get("form_selections", {})
    if form_selections:
        logger.info("[DEBUG] Processing form_selections: %s", form_selections)

        temp_permit_reason = form_selections.get("temporaryPermitReason", {})
        if temp_permit_reason:
            # temporary-1: temporaryPermitReason (체크박스 그룹 - 배열 형태)
            form_data_1 = _get_form_data(draft, "temporary-1")
            if form_data_1 is not None:
                # LLM이 리스트나 다른 타입으로 생성했을 수 있으므로 dict로 보장
                if "temporaryPermitReason" not in form_data_1 or not isinstance(form_data_1.get("temporaryPermitReason"), dict):
                    form_data_1["temporaryPermitReason"] = {}

                selected_reasons = []
                if temp_permit_reason.get("noApplicableStandards") is True:
                    selected_reasons.append("noApplicableStandards")
                if temp_permit_reason.get("unclearOrUnreasonableStandards") is True:
                    selected_reasons.append("unclearOrUnreasonableStandards")

                form_data_1["temporaryPermitReason"]["temporaryPermitReason"] = selected_reasons
                logger.info("[DEBUG] form_selections: temporary-1 temporaryPermitReason = %s", selected_reasons)

            # temporary-3: eligibility (소명서 - 개별 boolean 형태)
            form_data_3 = _get_form_data(draft, "temporary-3")
            if form_data_3 is not None:
                if "eligibility" not in form_data_3 or not isinstance(form_data_3.get("eligibility"), dict):
                    form_data_3["eligibility"] = {}

                if temp_permit_reason.get("noApplicableStandards") is True:
                    form_data_3["eligibility"]["noApplicableStandards"] = True
                    logger.info("[DEBUG] form_selections: noApplicableStandards = True")

                if temp_permit_reason.get("unclearOrUnreasonableStandards") is True:
                    form_data_3["eligibility"]["unclearOrUnreasonableStandards"] = True
                    logger.info("[DEBUG] form_selections: unclearOrUnreasonableStandards = True")

        # 실증특례 체크박스 처리 (demonstrationReason)
        demo_reason = form_selections.get("demonstrationReason", {})
        if demo_reason:
            # demonstration-1: regulatoryExemptionReason
            form_data_1 = _get_form_data(draft, "demonstration-1")
            if form_data_1 is not None:
                # LLM이 잘못 생성한 값 초기화 후 form_selections 값으로 설정
                form_data_1["regulatoryExemptionReason"] = {
                    "reason1_impossibleToApplyPermit": demo_reason.get("impossibleToApplyPermit") is True,
                    "reason2_unclearOrUnreasonableCriteria": demo_reason.get("unclearOrUnreasonableCriteria") is True,
                }
                logger.info("[DEBUG] form_selections: demo regulatoryExemptionReason = %s", form_data_1["regulatoryExemptionReason"])

            # demonstration-3: eligibility (소명서)
            form_data_3 = _get_form_data(draft, "demonstration-3")
            if form_data_3 is not None:
                # LLM이 잘못 생성한 값 초기화 후 form_selections 값으로 설정
                form_data_3["eligibility"] = {
                    "impossibleToApplyPermitByOtherLaw": demo_reason.get("impossibleToApplyPermit") is True,
                    "unclearOrUnreasonableCriteria": demo_reason.get("unclearOrUnreasonableCriteria") is True,
                }
                logger.info("[DEBUG] form_selections: demo eligibility = %s", form_data_3["eligibility"])

    # 신속확인(fastcheck) section_texts - LLM이 다듬어서 생성하도록 pass-through 제거
    # 서술형 필드는 LLM 프롬프트에 전달되어 다듬어진 결과가 사용됨
    # (메타데이터/숫자 필드만 pass-through, 서술형은 AI 다듬기)

    # ==============================
    # 해당여부에 대한 근거 (justification) pass-through
    # 소명서(temporary-3, demonstration-3)에 section_texts에서 직접 복사
    # 단, 트랙 변환 시에는 복사하지 않음 (LLM이 해당 트랙에 맞게 재작성)
    # ==============================
    justification_text = section_texts.get("justification")
    metadata = canonical.get("metadata", {})
    source_type = metadata.get("source_type", "")

    # 트랙 변환 여부 확인 (임시↔실증)
    is_track_conversion = (
        (source_type == "temp_permit" and target_track == "demo") or
        (source_type == "demo" and target_track == "temp_permit")
    )

    if justification_text and not is_track_conversion:
        # 같은 트랙이면 원문 그대로 복사
        for form_id in ["temporary-3", "demonstration-3"]:
            form_data = _get_form_data(draft, form_id)
            if form_data is not None:
                if "justification" not in form_data or not isinstance(form_data.get("justification"), dict):
                    form_data["justification"] = {}
                form_data["justification"]["justification"] = justification_text
                logger.info("[DEBUG] justification pass-through applied to %s", form_id)
    elif is_track_conversion:
        # 트랙 변환 시에는 LLM이 재작성하도록 빈 상태 유지
        logger.info("[DEBUG] 트랙 변환: justification은 LLM 재작성 필요 (pass-through 스킵)")

    # 신속확인 authority 필드 (regulatory에서만 추출 - 문서 기반)
    regulatory = canonical.get("regulatory", {})

    # regulatory에서만 찾기 (패턴 추출 결과만 신뢰)
    governing_agency = (
        regulatory.get("governing_agency")
        or regulatory.get("governingAgency")
        or regulatory.get("expected_agency")  # HWP 파서 키
    )
    permit_info = (
        regulatory.get("expected_permit")
        or regulatory.get("expectedPermit")
    )

    if governing_agency or permit_info:
        form_data = _get_form_data(draft, "fastcheck-1")
        if form_data is not None:
            if "authority" not in form_data:
                form_data["authority"] = {}
            if governing_agency:
                form_data["authority"]["expectedGoverningAgency"] = governing_agency
            if permit_info:
                form_data["authority"]["expectedPermitOrApproval"] = permit_info
            logger.info("[DEBUG] regulatory: authority applied to fastcheck-1")

    # NOTE: 체크박스 미선택 시 "체크 필요" 표시는 클라이언트에서 동적으로 처리
    # (DynamicFormCard.tsx의 isCheckboxOnlySection && !hasAnyCheckboxSelected)

    return draft


async def _generate_additional_questions(
    draft: dict,
    canonical: dict,
    target_track: str,
) -> dict:
    """임시허가/실증특례 → 신속확인 변환 시 기타 질의 사항 AI 추론 생성

    조건:
    - source_type이 temp_permit 또는 demo
    - target_track이 quick_check
    - additionalQuestions가 null인 경우

    생성된 내용에는 generated_by: "ai" 마킹을 추가합니다.
    """
    # 조건 체크
    metadata = canonical.get("metadata", {})
    source_type = metadata.get("source_type", "")

    # 임시허가/실증특례 → 신속확인 변환인 경우만
    if source_type not in ("temp_permit", "demo"):
        return draft
    if target_track != "quick_check":
        return draft

    # fastcheck-2의 additionalQuestions가 null인지 확인
    form_data = _get_form_data(draft, "fastcheck-2")
    if form_data is None:
        return draft

    current_value = form_data.get("additionalQuestions", {}).get("additionalQuestions")
    if current_value:  # 이미 값이 있으면 스킵
        return draft

    # 서비스 정보 추출
    service = canonical.get("service", {})
    service_info = f"""- 서비스명: {service.get("service_name", "N/A")}
- 서비스 설명: {service.get("service_description", "N/A")}
- 핵심 행위: {service.get("what_action", "N/A")}"""

    # 규제 정보 추출
    regulatory = canonical.get("regulatory", {})
    regulatory_issues = regulatory.get("regulatory_issues", [])
    regulatory_info = ""
    if regulatory_issues:
        for issue in regulatory_issues[:3]:  # 최대 3개만
            regulatory_info += f"- {issue.get('summary', '')}: {issue.get('blocking_reason', '')}\n"
    else:
        regulatory_info = "- 규제 이슈 정보 없음"

    # LLM 호출
    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )

        prompt = ADDITIONAL_QUESTIONS_PROMPT.format(
            service_info=service_info,
            regulatory_info=regulatory_info,
        )

        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        generated_text = response.content.strip()

        if generated_text:
            # additionalQuestions 필드에 AI 생성 내용 + 마킹 추가
            if "additionalQuestions" not in form_data or not isinstance(form_data.get("additionalQuestions"), dict):
                form_data["additionalQuestions"] = {}

            form_data["additionalQuestions"]["additionalQuestions"] = generated_text
            form_data["additionalQuestions"]["generated_by"] = "ai"

            logger.info("[DEBUG] AI generated additionalQuestions for track conversion")

    except Exception as e:
        logger.warning("additionalQuestions AI 생성 실패: %s", e)

    return draft


async def _generate_regulatory_exemption_reason(
    draft: dict,
    canonical: dict,
    target_track: str,
) -> dict:
    """신속확인 → 실증특례 변환 시 신청사유/해당여부 근거 AI 추론 생성

    조건:
    - source_type이 quick_check
    - target_track이 demo

    생성된 내용에는 generated_by: "ai" 마킹을 추가합니다.
    """
    metadata = canonical.get("metadata", {})
    source_type = metadata.get("source_type", "")

    # 신속확인 → 실증특례 변환인 경우만
    if source_type != "quick_check":
        return draft
    if target_track != "demo":
        return draft

    # 서비스 정보 추출
    service = canonical.get("service", {})
    service_info = f"""- 서비스명: {service.get("service_name", "N/A")}
- 서비스 설명: {service.get("service_description", "N/A")}
- 핵심 행위: {service.get("what_action", "N/A")}"""

    # 규제 정보 추출
    regulatory = canonical.get("regulatory", {})
    regulatory_issues = regulatory.get("regulatory_issues", [])
    regulatory_info = ""
    if regulatory_issues:
        for issue in regulatory_issues[:3]:
            regulatory_info += f"- {issue.get('summary', '')}: {issue.get('blocking_reason', '')}\n"
    else:
        regulatory_info = "- 규제 이슈 정보 없음"

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )

        prompt = REGULATORY_EXEMPTION_REASON_PROMPT.format(
            service_info=service_info,
            regulatory_info=regulatory_info,
        )

        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        raw_text = response.content.strip()

        # JSON 파싱
        json_text = raw_text
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        if json_match:
            json_text = json_match.group(1)

        result = json.loads(json_text)
        selected_reason = result.get("selectedReason", "")
        justification = result.get("justification", "")

        if selected_reason and justification:
            # demonstration-1: regulatoryExemptionReason 체크박스 + 마킹
            form_data_1 = _get_form_data(draft, "demonstration-1")
            if form_data_1 is not None:
                if "regulatoryExemptionReason" not in form_data_1 or not isinstance(form_data_1.get("regulatoryExemptionReason"), dict):
                    form_data_1["regulatoryExemptionReason"] = {}

                if selected_reason == "impossibleToApplyPermit":
                    form_data_1["regulatoryExemptionReason"]["reason1_impossibleToApplyPermit"] = True
                elif selected_reason == "unclearOrUnreasonableCriteria":
                    form_data_1["regulatoryExemptionReason"]["reason2_unclearOrUnreasonableCriteria"] = True

                form_data_1["regulatoryExemptionReason"]["generated_by"] = "ai"

            # demonstration-3: eligibility 체크박스 + justification + 마킹
            form_data_3 = _get_form_data(draft, "demonstration-3")
            if form_data_3 is not None:
                if "eligibility" not in form_data_3 or not isinstance(form_data_3.get("eligibility"), dict):
                    form_data_3["eligibility"] = {}

                if selected_reason == "impossibleToApplyPermit":
                    form_data_3["eligibility"]["impossibleToApplyPermitByOtherLaw"] = True
                elif selected_reason == "unclearOrUnreasonableCriteria":
                    form_data_3["eligibility"]["unclearOrUnreasonableCriteria"] = True

                form_data_3["eligibility"]["generated_by"] = "ai"

                # justification 텍스트
                if "justification" not in form_data_3 or not isinstance(form_data_3.get("justification"), dict):
                    form_data_3["justification"] = {}
                form_data_3["justification"]["justification"] = justification
                form_data_3["justification"]["generated_by"] = "ai"

            logger.info("[DEBUG] AI generated regulatoryExemptionReason for track conversion")

    except Exception as e:
        logger.warning("regulatoryExemptionReason AI 생성 실패: %s", e)

    return draft


async def _generate_temporary_permit_reason(
    draft: dict,
    canonical: dict,
    target_track: str,
) -> dict:
    """신속확인 → 임시허가 변환 시 신청사유/해당여부 근거 AI 추론 생성

    조건:
    - source_type이 quick_check
    - target_track이 temp_permit

    생성된 내용에는 generated_by: "ai" 마킹을 추가합니다.
    """
    metadata = canonical.get("metadata", {})
    source_type = metadata.get("source_type", "")

    # 신속확인 → 임시허가 변환인 경우만
    if source_type != "quick_check":
        return draft
    if target_track != "temp_permit":
        return draft

    # 서비스 정보 추출
    service = canonical.get("service", {})
    service_info = f"""- 서비스명: {service.get("service_name", "N/A")}
- 서비스 설명: {service.get("service_description", "N/A")}
- 핵심 행위: {service.get("what_action", "N/A")}"""

    # 규제 정보 추출
    regulatory = canonical.get("regulatory", {})
    regulatory_issues = regulatory.get("regulatory_issues", [])
    regulatory_info = ""
    if regulatory_issues:
        for issue in regulatory_issues[:3]:
            regulatory_info += f"- {issue.get('summary', '')}: {issue.get('blocking_reason', '')}\n"
    else:
        regulatory_info = "- 규제 이슈 정보 없음"

    try:
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )

        prompt = TEMPORARY_PERMIT_REASON_PROMPT.format(
            service_info=service_info,
            regulatory_info=regulatory_info,
        )

        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        raw_text = response.content.strip()

        # JSON 파싱
        json_text = raw_text
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        if json_match:
            json_text = json_match.group(1)

        result = json.loads(json_text)
        selected_reason = result.get("selectedReason", "")
        justification = result.get("justification", "")

        if selected_reason and justification:
            # temporary-3: eligibility 체크박스 + justification + 마킹
            form_data_3 = _get_form_data(draft, "temporary-3")
            if form_data_3 is not None:
                if "eligibility" not in form_data_3 or not isinstance(form_data_3.get("eligibility"), dict):
                    form_data_3["eligibility"] = {}

                if selected_reason == "noApplicableStandards":
                    form_data_3["eligibility"]["noApplicableStandards"] = True
                elif selected_reason == "unclearOrUnreasonableStandards":
                    form_data_3["eligibility"]["unclearOrUnreasonableStandards"] = True

                form_data_3["eligibility"]["generated_by"] = "ai"

                # justification 텍스트
                if "justification" not in form_data_3 or not isinstance(form_data_3.get("justification"), dict):
                    form_data_3["justification"] = {}
                form_data_3["justification"]["justification"] = justification
                form_data_3["justification"]["generated_by"] = "ai"

            logger.info("[DEBUG] AI generated temporaryPermitReason for track conversion")

    except Exception as e:
        logger.warning("temporaryPermitReason AI 생성 실패: %s", e)

    return draft


def _convert_temp_demo_reason(draft: dict, canonical: dict, target_track: str) -> dict:
    """임시허가 ↔ 실증특례 변환 시 사유 체크박스 처리

    임시허가(제37조)와 실증특례(제38조의2)는 신청 사유 조항이 법적으로 다르므로,
    트랙 변환 시 체크박스를 매핑하지 않고 빈 상태로 유지합니다.
    사용자가 직접 해당 트랙에 맞는 신청 사유를 선택해야 합니다.

    임시허가 제37조:
    - 제1항제1호: 기준·규격·요건 등이 없는 경우
    - 제1항제2호: 불명확하거나 불합리한 경우

    실증특례 제38조의2:
    - 제1항제1호: 허가 등을 신청하는 것이 불가능한 경우
    - 제1항제2호: 불명확하거나 불합리한 경우
    """
    metadata = canonical.get("metadata", {})
    source_type = metadata.get("source_type", "")

    # DEBUG: 트랙 변환 조건 확인
    print("\n[DEBUG _convert_temp_demo_reason]")
    print(f"  source_type: '{source_type}'")
    print(f"  target_track: '{target_track}'")

    # 트랙 변환이 발생하는 경우에만 "체크 필요" 표시 추가
    is_track_conversion = (
        (source_type == "temp_permit" and target_track == "demo") or
        (source_type == "demo" and target_track == "temp_permit")
    )
    print(f"  is_track_conversion: {is_track_conversion}")

    if is_track_conversion:
        # 실증특례로 변환 시
        if target_track == "demo":
            # demonstration-1: 신청 사유 체크박스
            form_data_1 = _get_form_data(draft, "demonstration-1")
            if form_data_1 is not None:
                form_data_1["regulatoryExemptionReason"] = {
                    "reason1_impossibleToApplyPermit": False,
                    "reason2_unclearOrUnreasonableCriteria": False,
                    "needs_check": True,  # 사용자 체크 필요 표시
                }
                logger.info("[DEBUG] demonstration-1 신청 사유: 체크 필요 표시 추가")

            # demonstration-3: 신청사유 체크박스 + 근거
            form_data_3 = _get_form_data(draft, "demonstration-3")
            if form_data_3 is not None:
                form_data_3["eligibility"] = {
                    "impossibleToApplyPermitByOtherLaw": False,
                    "unclearOrUnreasonableCriteria": False,
                    "needs_check": True,  # 사용자 체크 필요 표시
                }
                # justification은 LLM이 실증특례에 맞게 재작성 필요
                form_data_3["justification"] = {
                    "justification": "",
                    "needs_check": True,  # LLM 재작성 필요 표시
                }
                logger.info("[DEBUG] demonstration-3 신청사유: 체크 필요 표시 추가")

            # demonstration-2: 실증계획서 (임시허가 사업계획서와 용어/구조가 다름)
            form_data_2 = _get_form_data(draft, "demonstration-2")
            if form_data_2 is not None:
                # DEBUG: 변경 전 데이터 확인
                print("  [DEBUG] demonstration-2 변경 전:")
                print(f"    regulatoryExemption: {form_data_2.get('regulatoryExemption', 'N/A')}")

                # 모든 서술형 필드를 빈 상태로 + needs_check (LLM이 실증특례 용어로 재작성)
                form_data_2["technologyService"] = {
                    "detailedDescription": "",
                    "marketStatusAndOutlook": "",
                    "needs_check": True,
                }
                form_data_2["regulatoryExemption"] = {
                    "regulationDetails": "",
                    "necessityAndRequest": "",
                    "needs_check": True,
                }

                # DEBUG: 변경 후 데이터 확인
                print("  [DEBUG] demonstration-2 변경 후:")
                print(f"    regulatoryExemption: {form_data_2.get('regulatoryExemption', 'N/A')}")
                form_data_2["testPlan"] = {
                    "objectivesAndScope": "",
                    "executionMethod": "",
                    "schedule": "",
                    "needs_check": True,
                }
                form_data_2["operationPlan"] = {
                    "operationPlan": "",
                    "needs_check": True,
                }
                form_data_2["expectedEffects"] = {
                    "quantitative": "",
                    "qualitative": "",
                    "needs_check": True,
                }
                form_data_2["postTestPlan"] = {
                    "expansionPlan": "",
                    "restorationPlan": "",
                    "needs_check": True,
                }
                form_data_2["organizationAndBudget"] = {
                    "organizationStructure": "",
                    "budget": "",
                    "needs_check": True,
                }
                logger.info("[DEBUG] demonstration-2 실증계획서: 체크 필요 표시 추가")

            # demonstration-4: 이용자보호방안 (임시허가와 구조가 다름)
            form_data_4 = _get_form_data(draft, "demonstration-4")
            if form_data_4 is not None:
                # 모든 서술형 필드를 빈 상태로 + needs_check
                form_data_4["safetyVerification"] = {
                    "safetyVerification": "",
                    "needs_check": True,
                }
                form_data_4["userProtectionPlan"] = {
                    "userProtectionPlan": "",
                    "needs_check": True,
                }
                form_data_4["protectionAndResponse"] = {
                    "protectionAndResponse": "",
                    "needs_check": True,
                }
                form_data_4["riskAndMitigation"] = {
                    "riskAndMitigation": "",
                    "needs_check": True,
                }
                form_data_4["stakeholderConflict"] = {
                    "stakeholderConflict": "",
                    "needs_check": True,
                }
                logger.info("[DEBUG] demonstration-4 이용자보호방안: 체크 필요 표시 추가")

        # 임시허가로 변환 시
        elif target_track == "temp_permit":
            # temporary-1: 신청 사유 체크박스
            form_data_1 = _get_form_data(draft, "temporary-1")
            if form_data_1 is not None:
                form_data_1["temporaryPermitReason"] = {
                    "temporaryPermitReason": [],
                    "needs_check": True,  # 사용자 체크 필요 표시
                }
                logger.info("[DEBUG] temporary-1 신청 사유: 체크 필요 표시 추가")

            # temporary-3: 신청사유 체크박스 + 근거
            form_data_3 = _get_form_data(draft, "temporary-3")
            if form_data_3 is not None:
                form_data_3["eligibility"] = {
                    "noApplicableStandards": False,
                    "unclearOrUnreasonableStandards": False,
                    "needs_check": True,  # 사용자 체크 필요 표시
                }
                # justification은 LLM이 임시허가에 맞게 재작성 필요
                form_data_3["justification"] = {
                    "justification": "",
                    "needs_check": True,  # LLM 재작성 필요 표시
                }
                logger.info("[DEBUG] temporary-3 신청사유: 체크 필요 표시 추가")

            # temporary-2: 사업계획서 (실증특례 실증계획서와 용어/구조가 다름)
            form_data_2 = _get_form_data(draft, "temporary-2")
            if form_data_2 is not None:
                # 모든 서술형 필드를 빈 상태로 + needs_check (LLM이 임시허가 용어로 재작성)
                form_data_2["technologyService"] = {
                    "detailedDescription": "",
                    "marketStatusAndOutlook": "",
                    "needs_check": True,
                }
                form_data_2["temporaryPermitRequest"] = {
                    "regulationDetails": "",
                    "necessityAndRequest": "",
                    "needs_check": True,
                }
                form_data_2["businessPlan"] = {
                    "objectivesAndScope": "",
                    "businessContent": "",
                    "schedule": "",
                    "needs_check": True,
                }
                form_data_2["operationPlan"] = {
                    "operationPlan": "",
                    "needs_check": True,
                }
                form_data_2["expectedEffects"] = {
                    "quantitative": "",
                    "qualitative": "",
                    "needs_check": True,
                }
                form_data_2["expansionPlan"] = {
                    "expansionPlan": "",
                    "needs_check": True,
                }
                form_data_2["organizationAndBudget"] = {
                    "organizationStructure": "",
                    "budget": "",
                    "needs_check": True,
                }
                logger.info("[DEBUG] temporary-2 사업계획서: 체크 필요 표시 추가")

            # temporary-4: 안전성 검증 자료 및 이용자 보호방안 (실증특례와 구조가 다름)
            form_data_4 = _get_form_data(draft, "temporary-4")
            if form_data_4 is not None:
                # 모든 서술형 필드를 빈 상태로 + needs_check
                form_data_4["safetyVerification"] = {
                    "safetyVerification": "",
                    "needs_check": True,
                }
                form_data_4["userProtectionPlan"] = {
                    "userProtectionPlan": "",
                    "needs_check": True,
                }
                form_data_4["riskAndResponse"] = {
                    "riskAndResponse": "",
                    "needs_check": True,
                }
                form_data_4["stakeholderConflictResolution"] = {
                    "stakeholderConflictResolution": "",
                    "needs_check": True,
                }
                logger.info("[DEBUG] temporary-4 안전성검증/이용자보호: 체크 필요 표시 추가")

    return draft
