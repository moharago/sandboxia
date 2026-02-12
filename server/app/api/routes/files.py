"""파일 다운로드 API"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import supabase

router = APIRouter(prefix="/api/v1/files", tags=["files"])

STORAGE_BUCKET = "uploads"


@router.get("/download/{file_id}")
async def get_download_url(file_id: str):
    """파일 다운로드 URL 생성 (signed URL)"""
    # project_files 테이블에서 파일 정보 조회
    result = (
        supabase.table("project_files")
        .select("storage_path, file_name")
        .eq("id", file_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

    storage_path = result.data["storage_path"]
    file_name = result.data["file_name"]

    # signed URL 생성 (서버의 service role key 사용)
    # download 옵션으로 원본 파일명 지정
    url_result = supabase.storage.from_(STORAGE_BUCKET).create_signed_url(
        storage_path, 60, options={"download": file_name}
    )

    if url_result.get("error"):
        raise HTTPException(status_code=500, detail="다운로드 URL 생성 실패")

    return {"download_url": url_result["signedURL"]}
