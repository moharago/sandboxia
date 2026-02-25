"""Track Recommender 에이전트용 DB 서비스

track_results 테이블 CRUD 및 관련 데이터 조회
"""

import logging
from datetime import datetime

from app.core.config import settings, supabase

logger = logging.getLogger(__name__)


def get_project_canonical(project_id: str) -> dict | None:
    """프로젝트의 canonical 데이터 조회

    Args:
        project_id: 프로젝트 UUID

    Returns:
        canonical JSONB 데이터 또는 None
    """
    result = supabase.table("projects") \
        .select("canonical") \
        .eq("id", project_id) \
        .execute()

    if not result.data:
        return None

    return result.data[0].get("canonical")


def get_track_result(project_id: str) -> dict | None:
    """트랙 추천 결과 조회 (캐시)

    Args:
        project_id: 프로젝트 UUID

    Returns:
        track_results 레코드 또는 None (없으면)
    """
    result = supabase.table("track_results") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if not result.data:
        return None

    return result.data[0]


def save_track_result(
    project_id: str,
    recommended_track: str,
    confidence_score: float,
    result_summary: str,
    track_comparison: dict,
    similar_cases: list | None = None,
    domain_constraints: list | None = None,
) -> dict | None:
    """트랙 추천 결과 저장

    Args:
        project_id: 프로젝트 UUID
        recommended_track: AI 추천 트랙 ("demo" | "temp_permit" | "quick_check")
        confidence_score: 신뢰도 점수 (0-100)
        result_summary: AI 분석 요약 텍스트
        track_comparison: 트랙별 비교 데이터 (JSONB)
        similar_cases: 유사 승인 사례 목록 (JSONB)
        domain_constraints: 관련 법령 목록 (JSONB)

    Returns:
        생성된 track_results 레코드 또는 None (저장 실패 시)
    """
    result = supabase.table("track_results").upsert(
        {
            "project_id": project_id,
            "recommended_track": recommended_track,
            "confidence_score": confidence_score,
            "result_summary": result_summary,
            "track_comparison": track_comparison,
            "similar_cases": similar_cases or [],
            "domain_constraints": domain_constraints or [],
            "model_name": settings.LLM_MODEL,
        },
        on_conflict="project_id",
    ).execute()

    if not result.data:
        return None

    return result.data[0]


def update_project_track(project_id: str, track: str) -> dict | None:
    """프로젝트의 선택된 트랙 업데이트

    Args:
        project_id: 프로젝트 UUID
        track: 선택된 트랙 ("demo" | "temp_permit" | "quick_check")

    Returns:
        업데이트된 projects 레코드 또는 None (업데이트 실패 시)
    """
    result = supabase.table("projects") \
        .update({
            "track": track,
            "updated_at": datetime.now().isoformat()
        }) \
        .eq("id", project_id) \
        .execute()

    if not result.data:
        return None

    return result.data[0]


def update_project_after_track(project_id: str) -> dict | None:
    """트랙 추천 완료 후 프로젝트 업데이트

    - 항상 current_step을 3으로 설정 (track_recommender 에이전트 완료)
    - status: 1 (Step 1~3은 항상 status=1)

    Args:
        project_id: 프로젝트 UUID

    Returns:
        업데이트된 projects 레코드 또는 None
    """
    result = (
        supabase.table("projects")
        .update({
            "current_step": 3,  # track 에이전트 완료 → Step 3
            "status": 1,  # Step 1~3은 항상 status=1
        })
        .eq("id", project_id)
        .execute()
    )

    logger.info(f"[Track] 프로젝트 {project_id}: current_step → 3")

    return result.data[0] if result.data else None
