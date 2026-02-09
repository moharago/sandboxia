"""Service Structurer Agent 노드 함수

LangGraph 노드로 사용되는 함수들입니다.
"""

import json
import logging
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
        logger.info(
            f"HWP parsing completed: {success_count}/{len(parse_results)} successful"
        )

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
        logger.error(f"HWP parsing error: {e}")
        return {
            "hwp_parse_results": [],
            "error": f"HWP 파싱 오류: {str(e)}",
            "messages": [AIMessage(content=f"HWP 파싱 중 오류 발생: {str(e)}")],
        }


async def build_structure_node(state: ServiceStructurerState) -> dict[str, Any]:
    """Canonical Structure 생성 노드

    HWP 파싱 결과와 컨설턴트 입력을 병합하여
    LLM을 통해 Canonical Structure를 생성합니다.

    Args:
        state: 현재 상태

    Returns:
        canonical_structure 업데이트
    """
    hwp_parse_results = state.get("hwp_parse_results", [])
    consultant_input = state.get("consultant_input", {})
    session_id = state.get("session_id", "")
    requested_track = state.get("requested_track", DEFAULT_TRACK)

    # HWP 파싱 결과 병합
    merged_hwp_data = {}
    raw_text_combined = ""

    if hwp_parse_results:
        try:
            merged_hwp_data = merge_hwp_documents.invoke(
                {"parse_results": hwp_parse_results}
            )
            # 원문 텍스트 결합 (최대 50000자 - 사업계획서 전체 섹션 포함 필요)
            raw_texts = [
                r.get("raw_text", "")[:30000]  # 각 파일당 최대 30000자
                for r in hwp_parse_results
                if r.get("parse_success")
            ]
            raw_text_combined = "\n---\n".join(raw_texts)[:50000]
        except Exception as e:
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
        from app.agents.service_structurer.prompts import SYSTEM_PROMPT

        consultant_input_str = json.dumps(consultant_input, ensure_ascii=False, indent=2)
        merged_hwp_data_str = json.dumps(merged_hwp_data, ensure_ascii=False, indent=2)
        raw_text_str = raw_text_combined if raw_text_combined else "(원문 없음)"

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

## HWP 원문 텍스트 (참고용)
```
{raw_text_str}
```

## 요청된 트랙
{track_label}

## 세션 정보
- session_id: {session_id}

---

위 데이터를 분석하여 Canonical Structure JSON을 생성하세요. JSON만 출력하세요."""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]

        response = await llm.ainvoke(messages)
        response_text = response.content

        # JSON 파싱
        canonical_dict = _parse_llm_json_response(response_text)

        # Canonical Structure 검증 및 보완
        canonical_dict = _validate_and_complete_structure(
            canonical_dict, session_id, requested_track, consultant_input
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

        logger.info(f"Canonical structure created for session: {session_id}")

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


