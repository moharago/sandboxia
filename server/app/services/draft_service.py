"""Application Drafter 에이전트용 DB 서비스

projects.application_draft 컬럼에 초안 데이터 저장/조회
"""

import logging
from datetime import datetime

from app.agents.application_drafter import run_application_drafter
from app.core.config import supabase

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
    model_name: str = "gpt-4o-mini",
) -> dict | None:
    """초안 결과를 projects.application_draft에 저장

    Args:
        project_id: 프로젝트 UUID
        application_draft: AI가 개선한 폼 데이터 (application_input과 동일 구조)
        model_name: 사용된 LLM 모델명

    Returns:
        업데이트된 projects 레코드 또는 None
    """
    draft_data = {
        "form_values": application_draft,
        "model_name": model_name,
        "generated_at": datetime.now().isoformat(),
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
