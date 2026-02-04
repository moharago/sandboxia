"""Eligibility Evaluator 에이전트용 서비스

대상성 판단 비즈니스 로직 및 eligibility_results 테이블 CRUD
"""

import logging
from typing import Any, Literal

from app.agents.eligibility_evaluator.graph import run_eligibility_evaluation
from app.agents.eligibility_evaluator.schemas import EligibilityResult
from app.core.config import supabase

logger = logging.getLogger(__name__)


class EligibilityServiceError(Exception):
    """대상성 판단 서비스 오류"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_project_for_eligibility(project_id: str) -> dict | None:
    """대상성 판단을 위한 프로젝트 조회

    Args:
        project_id: 프로젝트 UUID

    Returns:
        프로젝트 데이터 (id, canonical, user_id) 또는 None
    """
    result = (
        supabase.table("projects")
        .select("id, canonical, user_id")
        .eq("id", project_id)
        .maybe_single()
        .execute()
    )

    return result.data if result else None


def get_eligibility_result(project_id: str) -> dict | None:
    """프로젝트의 대상성 판단 결과 조회

    Args:
        project_id: 프로젝트 UUID

    Returns:
        eligibility_results 레코드 또는 None
    """
    result = (
        supabase.table("eligibility_results")
        .select("*")
        .eq("project_id", project_id)
        .maybe_single()
        .execute()
    )

    return result.data if result else None


def save_eligibility_result(
    project_id: str,
    result: EligibilityResult,
) -> dict | None:
    """대상성 판단 결과 저장 (upsert)

    Args:
        project_id: 프로젝트 UUID
        result: EligibilityResult 객체

    Returns:
        저장된 eligibility_results 레코드 또는 None
    """
    eligibility_data = {
        "project_id": project_id,
        "eligibility_label": result.eligibility_label.value,
        "final_eligibility_label": None,  # 재분석 시 사용자 선택 초기화
        "confidence_score": result.confidence_score,
        "result_summary": result.result_summary,
        "direct_launch_risks": [r.model_dump() for r in result.direct_launch_risks],
        "evidence_data": result.evidence_data.model_dump(),
        "model_name": result.model_name,
    }

    # upsert: project_id가 있으면 UPDATE, 없으면 INSERT
    db_result = (
        supabase.table("eligibility_results")
        .upsert(eligibility_data, on_conflict="project_id")
        .execute()
    )

    return db_result.data[0] if db_result.data else None


def update_project_after_eligibility(project_id: str) -> dict | None:
    """대상성 판단 완료 후 프로젝트 업데이트

    - 최초 분석: current_step을 3으로 올림 (Step 2 완료 → Step 3으로 이동)
    - 재분석 (current_step >= 3): current_step을 2로 리셋
      (step 3+ 데이터는 유지하되, 사용자에게 재분석 필요를 알림)
    - status: 1 (재분석 시에도 status=1 유지)

    Args:
        project_id: 프로젝트 UUID

    Returns:
        업데이트된 projects 레코드 또는 None
    """
    # 현재 프로젝트의 current_step 조회
    project = (
        supabase.table("projects")
        .select("current_step")
        .eq("id", project_id)
        .maybe_single()
        .execute()
    )

    if not project.data:
        logger.error(f"프로젝트를 찾을 수 없습니다: {project_id}")
        return None

    current = project.data.get("current_step", 1)

    # 재분석인 경우 (이미 step 3 이상 진행) → step 2로 리셋
    # 최초 분석인 경우 → step 3으로 올림
    new_step = 2 if current >= 3 else 3

    result = (
        supabase.table("projects")
        .update({
            "current_step": new_step,
            "status": 1,
        })
        .eq("id", project_id)
        .execute()
    )

    if new_step == 2:
        logger.info(f"[재분석] 프로젝트 {project_id}: current_step {current} → 2로 리셋")

    return result.data[0] if result.data else None


def update_final_eligibility_label(
    project_id: str,
    final_eligibility_label: Literal["required", "not_required"],
) -> dict | None:
    """사용자의 최종 선택 저장

    Args:
        project_id: 프로젝트 UUID
        final_eligibility_label: 최종 선택 ("required" | "not_required")

    Returns:
        업데이트된 eligibility_results 레코드 또는 None
    """
    result = (
        supabase.table("eligibility_results")
        .update({"final_eligibility_label": final_eligibility_label})
        .eq("project_id", project_id)
        .execute()
    )

    return result.data[0] if result.data else None


async def run_eligibility(
    project_id: str,
    canonical: dict[str, Any],
) -> EligibilityResult:
    """대상성 판단 에이전트 실행

    Args:
        project_id: 프로젝트 UUID
        canonical: 서비스 정보 (projects.canonical)

    Returns:
        EligibilityResult 객체

    Raises:
        EligibilityServiceError: 에이전트 실행 실패 시
    """
    try:
        logger.info(f"[Eligibility] 대상성 판단 시작 - project_id: {project_id}")
        result = await run_eligibility_evaluation(
            project_id=project_id,
            canonical=canonical,
        )
        logger.info(
            f"[Eligibility] 대상성 판단 완료 - label: {result.eligibility_label.value}"
        )
        return result
    except Exception as e:
        logger.error(f"[Eligibility] 대상성 판단 실행 실패: {e}")
        raise EligibilityServiceError(
            f"대상성 판단 중 오류가 발생했습니다: {str(e)}",
            status_code=500,
        )
