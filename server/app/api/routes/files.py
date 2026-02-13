"""파일 다운로드 API"""

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from app.api.deps import AuthUser, get_auth_user
from app.core.config import supabase

router = APIRouter(prefix="/api/v1/files", tags=["files"])

STORAGE_BUCKET = "uploads"


@router.get("/download/{file_id}")
async def get_download_url(file_id: str, user: AuthUser = Depends(get_auth_user)):
    """파일 다운로드 URL 생성 (signed URL)

    인증된 사용자만 자신의 프로젝트 파일을 다운로드할 수 있습니다.
    """
    # project_files 테이블에서 파일 정보 및 project_id 조회
    try:
        file_result = (
            supabase.table("project_files")
            .select("storage_path, file_name, project_id")
            .eq("id", file_id)
            .single()
            .execute()
        )
    except APIError:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    if not file_result.data:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    project_id = file_result.data["project_id"]

    # 프로젝트 소유자 확인
    try:
        project_result = (
            supabase.table("projects")
            .select("user_id")
            .eq("id", project_id)
            .single()
            .execute()
        )
    except APIError:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    if not project_result.data:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    if project_result.data["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="이 파일에 대한 접근 권한이 없습니다")

    storage_path = file_result.data["storage_path"]
    file_name = file_result.data["file_name"]

    # signed URL 생성 (서버의 service role key 사용)
    # download 옵션으로 원본 파일명 지정
    url_result = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
        storage_path, 60, options={"download": file_name}
    )

    if url_result.get("error"):
        raise HTTPException(status_code=500, detail="다운로드 URL 생성 실패")

    return {"download_url": url_result["signedURL"]}
