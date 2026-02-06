"""
Project Service

프로젝트 공통 조회 및 권한 확인 로직
"""

from fastapi import HTTPException, status

from app.api.deps import AuthUser
from app.core.config import supabase


def get_project_or_404(project_id: str) -> dict:
    """
    프로젝트 ID로 프로젝트를 조회합니다.

    Returns:
        dict: 프로젝트 정보

    Raises:
        HTTPException 404: 프로젝트를 찾을 수 없는 경우
    """
    response = supabase.table("projects").select("*").eq("id", project_id).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )

    return response.data[0]


def verify_project_owner(project: dict, auth_user: AuthUser) -> None:
    """
    프로젝트 소유자인지 확인합니다.

    Args:
        project: 프로젝트 정보 (user_id 포함)
        auth_user: 인증된 사용자 정보

    Raises:
        HTTPException 403: 프로젝트 소유자가 아닌 경우
    """
    if project.get("user_id") != auth_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 프로젝트에 접근할 권한이 없습니다.",
        )


def get_authorized_project(project_id: str, auth_user: AuthUser) -> dict:
    """
    프로젝트를 조회하고 소유자인지 확인합니다.

    Args:
        project_id: 프로젝트 ID
        auth_user: 인증된 사용자 정보

    Returns:
        dict: 프로젝트 정보

    Raises:
        HTTPException 404: 프로젝트를 찾을 수 없는 경우
        HTTPException 403: 프로젝트 소유자가 아닌 경우
    """
    project = get_project_or_404(project_id)
    verify_project_owner(project, auth_user)
    return project
