"""Service Structurer Agent 노드 함수

LangGraph 노드로 사용되는 함수들입니다.
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from app.agents.service_structurer.state import ServiceStructurerState
from app.agents.service_structurer.tools import (
    merge_hwp_documents,
    parse_hwp_documents,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# 기본 트랙 (상담신청)
DEFAULT_TRACK = "counseling"


async def parse_hwp_node(state: ServiceStructurerState) -> dict[str, Any]:
    """HWP 파일 파싱 노드

    업로드된 HWP 파일들을 파싱하여 구조화된 데이터로 변환합니다.

    Args:
        state: 현재 상태

    Returns:
        hwp_parse_results 업데이트
    """
    start_time = time.time()
    print("\n[Step1] ========== HWP 파싱 시작 ==========")

    file_paths = state.get("file_paths", [])
    file_subtypes = state.get("file_subtypes", [])

    if not file_paths:
        logger.warning("No HWP files to parse")
        return {
            "hwp_parse_results": [],
            "messages": [AIMessage(content="파싱할 HWP 파일이 없습니다.")],
        }

    try:
        # HWP 파일 파싱
        parse_results = parse_hwp_documents.invoke(
            {
                "file_paths": file_paths,
                "document_subtypes": file_subtypes if file_subtypes else None,
            }
        )

        # 파싱 성공/실패 로깅
        success_count = sum(1 for r in parse_results if r.get("parse_success"))
        elapsed = time.time() - start_time
        print(f"[Step1] HWP 파싱 완료: {success_count}/{len(parse_results)}개 성공 ({elapsed:.2f}초)")

        return {
            "hwp_parse_results": parse_results,
            "messages": [
                AIMessage(
                    content=f"HWP 파일 {len(parse_results)}개 파싱 완료 "
                    f"(성공: {success_count}개)"
                )
            ],
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[Step1] HWP 파싱 오류 ({elapsed:.2f}초): {e}")
        return {
            "hwp_parse_results": [],
            "error": f"HWP 파싱 오류: {str(e)}",
            "messages": [AIMessage(content=f"HWP 파싱 중 오류 발생: {str(e)}")],
        }


async def build_structure_node(state: ServiceStructurerState) -> dict[str, Any]:
    """Canonical Structure 생성 노드

    HWP 파싱 결과와 컨설턴트 입력을 병합하여
    LLM을 통해 Canonical Structure를 생성합니다.

    최적화: HWP 파서가 추출한 섹션 텍스트를 직접 사용하여
    LLM 컨텍스트 크기를 줄이고 속도를 개선합니다.

    Args:
        state: 현재 상태

    Returns:
        canonical_structure 업데이트
    """
    total_start = time.time()
    print("\n[Step1] ========== Canonical 구조 생성 시작 ==========")

    hwp_parse_results = state.get("hwp_parse_results", [])
    consultant_input = state.get("consultant_input", {})
    session_id = state.get("session_id", "")
    requested_track = state.get("requested_track", DEFAULT_TRACK)

    # HWP 파싱 결과 병합
    merged_hwp_data = {}
    pre_built_section_texts = {}

    if hwp_parse_results:
        try:
            merge_start = time.time()
            merged_hwp_data = merge_hwp_documents.invoke(
                {"parse_results": hwp_parse_results}
            )
            # [최적화] HWP 파서가 추출한 섹션 텍스트를 직접 매핑
            # raw_text를 LLM에 보내는 대신, 이미 추출된 필드를 사용
            pre_built_section_texts = _build_section_texts_from_hwp(
                hwp_parse_results, merged_hwp_data
            )
            merge_elapsed = time.time() - merge_start
            print(f"[Step1] HWP 병합 완료 ({merge_elapsed:.2f}초)")
            print(f"[Step1] section_texts 직접 추출: {len(pre_built_section_texts)}개 필드")
        except Exception as e:
            print(f"[Step1] HWP 병합 오류: {e}")
            logger.error(f"HWP merge error: {e}")

    # LLM 호출
    try:
        # 트랙 → 한글명 매핑 (프롬프트용)
        track_labels = {
            "counseling": "상담신청",
            "quick_check": "신속확인",
            "temp_permit": "임시허가",
            "demo": "실증특례",
        }
        track_label = track_labels.get(requested_track, requested_track)

        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.1,
            api_key=settings.OPENAI_API_KEY,
        )

        # 프롬프트 직접 구성 (ChatPromptTemplate의 중괄호 문제 완전 회피)
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.agents.service_structurer.prompts import SYSTEM_PROMPT_OPTIMIZED

        consultant_input_str = json.dumps(consultant_input, ensure_ascii=False, indent=2)
        merged_hwp_data_str = json.dumps(merged_hwp_data, ensure_ascii=False, indent=2)

        # [재무/인력 추출용] 사업계획서에서 재무/인력 테이블 섹션만 추출
        financial_hr_text = _extract_financial_hr_sections(hwp_parse_results)

        # Human 메시지 직접 구성 (f-string 사용, 템플릿 시스템 우회)
        human_content = f"""다음 데이터를 분석하여 Canonical Structure를 생성하세요.

## 컨설턴트 입력 데이터
```json
{consultant_input_str}
```

## HWP 파싱 결과 (병합됨)
```json
{merged_hwp_data_str}
```

## 재무/인력 테이블 원문 (추출용)
```
{financial_hr_text}
```

## 요청된 트랙
{track_label}

## 세션 정보
- session_id: {session_id}

---

위 데이터를 분석하여 Canonical Structure JSON을 생성하세요.
- **section_texts는 시스템이 자동 병합하므로 빈 객체 {{}}로 출력하세요!**
- **financial, hr는 붙임 문서 원문에서 테이블 데이터를 추출하세요!**
- LLM이 생성: company, service(what_action, target_users 등), technology, regulatory, financial, hr, project_plan, applicants, form_selections, metadata
JSON만 출력하세요."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT_OPTIMIZED),
            HumanMessage(content=human_content),
        ]

        # 토큰 수 추정 출력
        total_chars = len(SYSTEM_PROMPT_OPTIMIZED) + len(human_content)
        print(f"[Step1] LLM 호출 시작 (입력 약 {total_chars:,}자, ~{total_chars//8:,} 토큰)")
        llm_start = time.time()

        response = await llm.ainvoke(messages)
        response_text = response.content

        llm_elapsed = time.time() - llm_start
        print(f"[Step1] LLM 응답 완료 ({llm_elapsed:.2f}초, 출력 {len(response_text):,}자)")

        # JSON 파싱
        canonical_dict = _parse_llm_json_response(response_text)

        # Canonical Structure 검증 및 보완
        canonical_dict = _validate_and_complete_structure(
            canonical_dict, session_id, requested_track, consultant_input
        )

        # [최적화 v2] section_texts 강제 적용 (LLM은 빈 객체 출력)
        # LLM 출력 토큰 절약: section_texts를 복사하지 않고 여기서 직접 병합
        if pre_built_section_texts:
            canonical_dict["section_texts"] = pre_built_section_texts.copy()
            logger.info(
                f"[Optimized] section_texts applied: {len(pre_built_section_texts)} fields"
            )

        # HWP 파서에서 추출한 form_selections 강제 적용 (LLM 파싱보다 우선)
        if merged_hwp_data.get("form_selections"):
            hwp_form_selections = merged_hwp_data["form_selections"]
            if "form_selections" not in canonical_dict:
                canonical_dict["form_selections"] = {}
            # HWP 파서 결과로 덮어씀 (LLM이 잘못 파싱했을 수 있으므로)
            for key, value in hwp_form_selections.items():
                canonical_dict["form_selections"][key] = value
                logger.info(f"[HWP Parser] form_selections[{key}] = {value}")

        # HWP 파서에서 추출한 signatures 강제 적용
        if merged_hwp_data.get("applicants", {}).get("signatures"):
            hwp_signatures = merged_hwp_data["applicants"]["signatures"]
            if "applicants" not in canonical_dict:
                canonical_dict["applicants"] = {}
            canonical_dict["applicants"]["signatures"] = hwp_signatures
            logger.info(f"[HWP Parser] applicants.signatures = {hwp_signatures}")

        # HWP 파서에서 추출한 establishment_date 강제 적용
        hwp_establishment_date = merged_hwp_data.get("company_info", {}).get("establishment_date")
        if hwp_establishment_date:
            if "company" not in canonical_dict:
                canonical_dict["company"] = {}
            canonical_dict["company"]["establishment_date"] = hwp_establishment_date
            logger.info(f"[HWP Parser] company.establishment_date = {hwp_establishment_date}")

        # HWP 파서에서 추출한 application_date/submission_date 강제 적용
        hwp_applicants = merged_hwp_data.get("applicants", {})
        if hwp_applicants.get("application_date"):
            if "applicants" not in canonical_dict:
                canonical_dict["applicants"] = {}
            canonical_dict["applicants"]["applicationDate"] = hwp_applicants["application_date"]
            logger.info(f"[HWP Parser] applicants.applicationDate = {hwp_applicants['application_date']}")
        if hwp_applicants.get("submission_date"):
            if "applicants" not in canonical_dict:
                canonical_dict["applicants"] = {}
            canonical_dict["applicants"]["submissionDate"] = hwp_applicants["submission_date"]
            logger.info(f"[HWP Parser] applicants.submissionDate = {hwp_applicants['submission_date']}")

        # HWP 파서에서 추출한 service_description 강제 적용 (원본 줄바꿈 보존)
        hwp_service_description = merged_hwp_data.get("service_info", {}).get("service_description")
        if hwp_service_description and len(hwp_service_description.strip()) > 10:
            if "service" not in canonical_dict:
                canonical_dict["service"] = {}
            canonical_dict["service"]["service_description"] = hwp_service_description.strip()
            logger.info(f"[HWP Parser] service.service_description applied (원본 {len(hwp_service_description)}자)")

        # startDate와 durationMonths로 endDate 계산 (없는 경우)
        project_plan = canonical_dict.get("project_plan", {})
        if project_plan.get("startDate") and project_plan.get("durationMonths") and not project_plan.get("endDate"):
            end_date = _calculate_end_date(project_plan["startDate"], project_plan["durationMonths"])
            if end_date:
                canonical_dict["project_plan"]["endDate"] = end_date
                logger.info(f"[Calculated] project_plan.endDate = {end_date}")

        total_elapsed = time.time() - total_start
        print(f"[Step1] ========== Canonical 구조 생성 완료 ({total_elapsed:.2f}초) ==========\n")

        return {
            "canonical_structure": canonical_dict,
            "messages": [
                AIMessage(
                    content=f"Canonical Structure 생성 완료. "
                    f"누락 필드: {canonical_dict.get('metadata', {}).get('missing_fields', [])}"
                )
            ],
        }

    except Exception as e:
        import traceback
        total_elapsed = time.time() - total_start
        print(f"[Step1] ========== Canonical 구조 생성 실패 ({total_elapsed:.2f}초) ==========")
        print(f"[Step1] 오류: {e}")
        logger.error(f"Structure building error: {e}")
        logger.error(f"Structure building traceback:\n{traceback.format_exc()}")
        return {
            "canonical_structure": None,
            "error": f"LLM 구조화 오류: {str(e)}",
            "messages": [AIMessage(content=f"구조화 실패: {str(e)}")],
        }


def _parse_llm_json_response(response_text: str) -> dict[str, Any]:
    """LLM 응답에서 JSON 파싱"""
    # JSON 블록 추출
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end == -1:
            # 닫는 ``` 없으면 끝까지
            json_str = response_text[start:].strip()
        else:
            json_str = response_text[start:end].strip()
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end == -1:
            json_str = response_text[start:].strip()
        else:
            json_str = response_text[start:end].strip()
    else:
        json_str = response_text.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # JSON 파싱 실패 시 디버그 로깅
        logger.error(f"[JSON Parse Error] {e}")
        logger.error(f"[JSON Parse Error] json_str 시작 200자: {json_str[:200]}")
        logger.error(f"[JSON Parse Error] json_str 끝 200자: {json_str[-200:]}")
        raise


def _build_section_texts_from_hwp(
    hwp_parse_results: list[dict[str, Any]],
    merged_hwp_data: dict[str, Any],
) -> dict[str, str]:
    """HWP 파싱 결과에서 section_texts 직접 구성

    HWP 파서가 추출한 섹션 텍스트를 canonical의 section_texts 형식으로 매핑합니다.
    이를 통해 LLM이 raw_text에서 다시 추출할 필요 없이 바로 사용할 수 있습니다.

    Args:
        hwp_parse_results: HWP 파싱 결과 리스트
        merged_hwp_data: 병합된 HWP 데이터

    Returns:
        section_texts 딕셔너리 (camelCase 키)
    """
    # HWP 파서 필드명 → section_texts 키 매핑
    field_mapping = {
        # technology_info 그룹
        "detailed_description": "detailedDescription",
        "market_status": "marketStatusAndOutlook",
        # regulatory_info 그룹
        "regulation_details": "regulationDetails",
        "necessity_and_request": "necessityAndRequest",
        "legal_issues": "legalIssues",  # 신속확인용
        "related_laws": "relatedLaws",  # 신속확인용
        "regulatory_issues": "regulatoryIssues",  # 신속확인용
        # service_info 그룹 (신속확인용)
        "technology_service_details": "technologyServiceDetails",
        "additional_questions": "additionalQuestions",
        # business_plan 그룹
        "objectives_and_scope": "objectivesAndScope",
        "business_content": "businessContent",
        "schedule": "schedule",
        "operation_plan": "operationPlan",
        "expected_quantitative": "quantitativeEffect",
        "expected_qualitative": "qualitativeEffect",
        "expansion_plan": "expansionPlan",
        "restoration_plan": "restorationPlan",
        "organization_structure": "organizationStructure",
        "budget": "budget",
        # safety_and_protection 그룹
        "safety_verification": "safetyVerification",
        "user_protection_plan": "userProtectionPlan",
        "risk_and_response": "riskAndResponse",
        "stakeholder_conflict": "stakeholderConflictResolution",
        # justification 그룹
        "justification": "justification",
        # company_info 그룹
        "main_business": "mainBusiness",
        "licenses_and_permits": "licensesAndPermits",
        "technologies_and_patents": "technologiesAndPatents",
    }

    section_texts = {}

    # 1. merged_hwp_data의 각 그룹에서 필드 추출
    groups = [
        "technology_info",
        "regulatory_info",
        "business_plan",
        "safety_and_protection",
        "justification",
        "company_info",
        "service_info",  # 신속확인용
    ]

    for group in groups:
        group_data = merged_hwp_data.get(group, {})
        if isinstance(group_data, dict):
            for hwp_field, section_key in field_mapping.items():
                if hwp_field in group_data and group_data[hwp_field]:
                    value = group_data[hwp_field]
                    # 문자열이고 충분한 길이가 있으면 추가
                    if isinstance(value, str) and len(value.strip()) > 10:
                        section_texts[section_key] = value.strip()

    # 2. 개별 파싱 결과의 extracted_fields에서도 추출 (merged에서 누락된 경우)
    for result in hwp_parse_results:
        if not result.get("parse_success"):
            continue
        extracted = result.get("extracted_fields", {})
        for hwp_field, section_key in field_mapping.items():
            # 이미 있으면 스킵
            if section_key in section_texts:
                continue
            if hwp_field in extracted and extracted[hwp_field]:
                value = extracted[hwp_field]
                if isinstance(value, str) and len(value.strip()) > 10:
                    section_texts[section_key] = value.strip()

    return section_texts


def _validate_and_complete_structure(
    canonical_dict: dict[str, Any],
    session_id: str,
    requested_track: str,
    consultant_input: dict[str, Any],
) -> dict[str, Any]:
    """Canonical Structure 검증 및 보완"""

    # 메타데이터 보완
    if "metadata" not in canonical_dict:
        canonical_dict["metadata"] = {}

    metadata = canonical_dict["metadata"]
    metadata["session_id"] = session_id
    metadata["source_type"] = requested_track  # 트랙 값 그대로 사용
    metadata["created_at"] = datetime.now().isoformat()

    # 컨설턴트 메모 추가
    if consultant_input.get("memo"):
        metadata["consultant_memo"] = consultant_input["memo"]

    # 누락 필드 계산
    missing_fields = []
    service = canonical_dict.get("service", {})

    if not service.get("service_name"):
        missing_fields.append("service.service_name")
    if not service.get("what_action"):
        missing_fields.append("service.what_action")
    if not service.get("target_users"):
        missing_fields.append("service.target_users")
    if not service.get("delivery_method"):
        missing_fields.append("service.delivery_method")
    if not service.get("service_description"):
        missing_fields.append("service.service_description")

    metadata["missing_fields"] = missing_fields

    # 신뢰도 검증
    if "field_confidence" not in metadata:
        metadata["field_confidence"] = {
            "company": 0.5,
            "service": 0.5,
            "technology": 0.3,
            "regulatory": 0.3,
        }

    return canonical_dict


def _extract_financial_hr_sections(hwp_parse_results: list[dict[str, Any]]) -> str:
    """HWP 파싱 결과에서 재무/인력 테이블 + 주요내용 섹션 추출

    전체 raw_text 대신 필요한 섹션만 추출하여 LLM 입력 토큰을 줄입니다.

    Args:
        hwp_parse_results: HWP 파싱 결과 리스트

    Returns:
        추출된 섹션 텍스트 (없으면 빈 문자열)
    """
    sections = []

    # 문서별 raw_text 수집
    doc_texts = {}
    for result in hwp_parse_results:
        if result.get("parse_success"):
            subtype = result.get("document_subtype", "")
            raw = result.get("raw_text", "")
            if raw:
                doc_texts[subtype] = raw

    # 1. 신청서(temporary-1, demonstration-1)에서 "주요내용" 추출
    application_subtypes = ["temporary-1", "demonstration-1"]
    found_main_content = False
    for subtype in application_subtypes:
        if found_main_content:
            break
        if subtype in doc_texts:
            raw = doc_texts[subtype]
            # "주요내용" 또는 "신규 기술·서비스" 섹션 추출
            main_content_patterns = [
                r"주요\s*내용\s*([\s\S]*?)(?=임시허가|실증특례|신청\s*사유|\Z)",
                r"신규\s*기술[·‧\s]*서비스\s*([\s\S]*?)(?=임시허가|실증특례|신청\s*사유|\Z)",
            ]
            for pattern in main_content_patterns:
                match = re.search(pattern, raw, re.IGNORECASE)
                if match:
                    content = match.group(1).strip()
                    if len(content) > 50:  # 의미있는 내용만
                        if len(content) > 2000:
                            content = content[:2000]
                        sections.append(f"[주요내용 - 신청서]\n{content}")
                        print(f"[Step1] 주요내용 섹션 추출: {len(content):,}자")
                        found_main_content = True
                        break

    # 2. 사업계획서(temporary-2, demonstration-2)에서 재무/인력 추출
    plan_subtypes = ["temporary-2", "demonstration-2"]
    plan_raw = ""
    for subtype in plan_subtypes:
        if subtype in doc_texts:
            plan_raw = doc_texts[subtype]
            break

    # 사업계획서에서 못 찾으면 재무/인력 키워드 있는 문서 찾기
    if not plan_raw or ("재무" not in plan_raw and "인력" not in plan_raw):
        for subtype, raw in doc_texts.items():
            if "재무" in raw or "인력" in raw:
                plan_raw = raw
                break

    if plan_raw:
        # 재무상태/재무현황 섹션 추출
        financial_patterns = [
            r"(재무상태[\s\S]*?(?=주요인력|인력현황|조직도|\Z))",
            r"(재무현황[\s\S]*?(?=주요인력|인력현황|조직도|\Z))",
        ]
        for pattern in financial_patterns:
            match = re.search(pattern, plan_raw, re.IGNORECASE)
            if match:
                financial_section = match.group(1).strip()
                if len(financial_section) > 2000:
                    financial_section = financial_section[:2000]
                sections.append(f"[재무현황]\n{financial_section}")
                print(f"[Step1] 재무현황 섹션 추출: {len(financial_section):,}자")
                break

        # 인력현황/주요인력 섹션 추출
        hr_patterns = [
            r"(주요인력\s*현황[\s\S]*?(?=재무|붙임|\Z))",
            r"(인력현황[\s\S]*?(?=재무|붙임|\Z))",
            r"(조직도[\s\S]*?(?=재무|붙임|\Z))",
        ]
        for pattern in hr_patterns:
            match = re.search(pattern, plan_raw, re.IGNORECASE)
            if match:
                hr_section = match.group(1).strip()
                if len(hr_section) > 2000:
                    hr_section = hr_section[:2000]
                sections.append(f"[인력현황]\n{hr_section}")
                print(f"[Step1] 인력현황 섹션 추출: {len(hr_section):,}자")
                break

    if not sections:
        print("[Step1] ⚠️ 필요 섹션 추출 실패")
        return ""

    result = "\n\n".join(sections)
    print(f"[Step1] 추출 텍스트 총 {len(result):,}자")
    return result


def _calculate_end_date(start_date: str, duration_months: int) -> str | None:
    """startDate와 durationMonths로 endDate 계산

    Args:
        start_date: 시작일 문자열 (예: "2026년4월", "2026년 4월", "2026.04")
        duration_months: 기간 (월 단위)

    Returns:
        종료일 문자열 (예: "2026년9월") 또는 None
    """
    try:
        # 연도와 월 추출
        year_match = re.search(r"(\d{4})", start_date)
        month_match = re.search(r"(\d{1,2})(?:월|\.)", start_date)

        if not year_match or not month_match:
            # "2026년4월" 형식 재시도
            match = re.search(r"(\d{4})년\s*(\d{1,2})", start_date)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
            else:
                return None
        else:
            year = int(year_match.group(1))
            month = int(month_match.group(1))

        # 종료월 계산
        end_month = month + duration_months - 1
        end_year = year + (end_month - 1) // 12
        end_month = ((end_month - 1) % 12) + 1

        return f"{end_year}년{end_month}월"

    except Exception as e:
        logger.warning(f"endDate 계산 실패: {e}")
        return None


