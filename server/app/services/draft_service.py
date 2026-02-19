"""Application Drafter 에이전트용 DB 서비스

projects.application_draft 컬럼에 초안 데이터 저장/조회
"""

import logging
from datetime import datetime

from app.agents.application_drafter import run_application_drafter
from app.core.config import supabase
from app.services.utils import is_flat_structure, unflatten

logger = logging.getLogger(__name__)


class DraftServiceError(Exception):
    """Draft 서비스 에러"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_project_data_for_draft(project_id: str) -> dict | None:
    """프로젝트의 canonical + track 데이터 조회

    Args:
        project_id: 프로젝트 UUID

    Returns:
        프로젝트 데이터 (canonical, track 포함) 또는 None
    """
    result = supabase.table("projects") \
        .select("id, canonical, track, user_id") \
        .eq("id", project_id) \
        .maybe_single() \
        .execute()

    if not result.data:
        return None

    return result.data


def save_draft_result(
    project_id: str,
    application_draft: dict,
    track: str,
    model_name: str = "gpt-4o-mini",
    similar_cases: list | None = None,
    domain_laws: list | None = None,
) -> dict | None:
    """초안 결과를 projects.application_draft에 저장

    Args:
        project_id: 프로젝트 UUID
        application_draft: AI가 개선한 폼 데이터 (application_input과 동일 구조)
        track: 초안 생성에 사용된 트랙 ("demo" | "temp_permit" | "quick_check")
        model_name: 사용된 LLM 모델명
        similar_cases: RAG 검색된 유사 승인 사례
        domain_laws: RAG 검색된 관련 법령

    Returns:
        업데이트된 projects 레코드 또는 None
    """
    # LLM 출력이 이미 {form_id: {data: {...}, formId: ...}} 구조이므로
    # 추가 래핑 없이 그대로 저장
    # track 필드를 추가하여 클라이언트에서 트랙 불일치 감지 가능
    draft_data = {
        "form_values": application_draft,
        "track": track,
        "model_name": model_name,
        "generated_at": datetime.now().isoformat(),
        "similar_cases": similar_cases or [],
        "domain_laws": domain_laws or [],
    }

    try:
        result = supabase.table("projects") \
            .update({
                "application_draft": draft_data,
                "updated_at": datetime.now().isoformat(),
            }) \
            .eq("id", project_id) \
            .execute()
    except Exception as e:
        logger.error("Draft 저장 실패 (project_id=%s): %s", project_id, e)
        return None

    if not result.data or len(result.data) == 0:
        logger.warning("Draft 저장 후 데이터 없음 (project_id=%s)", project_id)
        return None

    return result.data[0]


def update_draft_card(
    project_id: str,
    card_key: str,
    card_data: dict,
) -> dict | None:
    """특정 카드만 부분 업데이트 (JSON 병합)

    기존 application_draft.form_values에서 해당 카드만 업데이트하고
    나머지 카드는 그대로 유지합니다.

    Args:
        project_id: 프로젝트 UUID
        card_key: 업데이트할 카드 키 (예: "fastcheck_application")
        card_data: 카드 데이터 (flat된 필드-값 쌍)

    Returns:
        업데이트된 projects 레코드 또는 None
    """
    try:
        # 1. 기존 draft 데이터 조회
        result = supabase.table("projects") \
            .select("application_draft") \
            .eq("id", project_id) \
            .maybe_single() \
            .execute()

        if not result.data:
            logger.warning("프로젝트를 찾을 수 없음 (project_id=%s)", project_id)
            return None

        # 2. 기존 데이터에서 form_values 추출 또는 초기화
        existing_draft = result.data.get("application_draft") or {}
        existing_form_values = existing_draft.get("form_values") or {}

        # 3. flat 구조면 nested로 변환
        if is_flat_structure(card_data):
            card_data = unflatten(card_data)

        # 4. 해당 카드만 업데이트 (병합)
        updated_form_values = {
            **existing_form_values,
            card_key: {"data": card_data},
        }

        # 4. 전체 draft 구조 업데이트
        updated_draft = {
            **existing_draft,
            "form_values": updated_form_values,
            "updated_at": datetime.now().isoformat(),
        }

        # 5. DB 저장
        update_result = supabase.table("projects") \
            .update({
                "application_draft": updated_draft,
                "updated_at": datetime.now().isoformat(),
            }) \
            .eq("id", project_id) \
            .execute()

        if not update_result.data or len(update_result.data) == 0:
            logger.warning("Draft 카드 업데이트 후 데이터 없음 (project_id=%s)", project_id)
            return None

        logger.info("Draft 카드 업데이트 완료: project=%s, card=%s", project_id, card_key)
        return update_result.data[0]

    except Exception as e:
        logger.error("Draft 카드 업데이트 실패 (project_id=%s, card=%s): %s", project_id, card_key, e)
        return None


async def run_draft(
    project_id: str,
    canonical: dict,
    track: str,
) -> dict:
    """Application Drafter Agent 실행 래퍼

    Args:
        project_id: 프로젝트 UUID
        canonical: canonical 구조화 데이터
        track: 선택된 트랙 ("demo" | "temp_permit" | "quick_check")

    Returns:
        에이전트 실행 결과 딕셔너리

    Raises:
        DraftServiceError: 에이전트 실행 실패 시
    """
    try:
        result = await run_application_drafter(
            project_id=project_id,
            canonical=canonical,
            track=track,
        )
        return result
    except Exception as e:
        logger.error("Application Drafter 실행 실패: %s", e, exc_info=True)
        raise DraftServiceError(
            message=f"신청서 초안 생성 중 오류가 발생했습니다: {str(e)}",
            status_code=500,
        )
