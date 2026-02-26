"""파일 다운로드 API"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from storage3.exceptions import StorageApiError

from app.api.deps import AuthUser, get_auth_user
from app.core.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])

STORAGE_BUCKET = "uploads"


@router.get("/download/{file_id}")
def get_download_url(file_id: str, user: AuthUser = Depends(get_auth_user)):
    """파일 다운로드 URL 생성 (signed URL)

    인증된 사용자만 자신의 프로젝트 파일을 다운로드할 수 있습니다.
    """
    # project_files 테이블에서 파일 정보 및 project_id 조회
    file_result = (
        supabase.table("project_files")
        .select("storage_path, file_name, project_id")
        .eq("id", file_id)
        .maybe_single()
        .execute()
    )

    if not file_result.data:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    project_id = file_result.data["project_id"]

    # 프로젝트 소유자 확인
    project_result = (
        supabase.table("projects")
        .select("user_id")
        .eq("id", project_id)
        .maybe_single()
        .execute()
    )

    if not project_result.data:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    if project_result.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="이 파일에 대한 접근 권한이 없습니다")

    storage_path = file_result.data["storage_path"]
    file_name = file_result.data["file_name"]

    # signed URL 생성 (서버의 service role key 사용)
    # download 옵션으로 원본 파일명 지정
    try:
        url_result = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
            storage_path, 60, options={"download": file_name}
        )
    except StorageApiError as e:
        logger.error(f"Storage API error for file {file_id}: {e}")
        # 스토리지에 파일이 없는 경우 (DB 레코드만 존재)
        raise HTTPException(
            status_code=404,
            detail="파일이 스토리지에 존재하지 않습니다. 파일을 다시 업로드해주세요.",
        )

    if url_result.get("error"):
        raise HTTPException(status_code=500, detail="다운로드 URL 생성 실패")

    return {"download_url": url_result["signedURL"]}
