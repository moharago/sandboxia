import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_auth_user
from app.core.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 유저 삭제 (service_role 필요)
# ================================
@router.delete("/users/me")
def delete_user(auth_user=Depends(get_auth_user)):
    """본인 계정 삭제

    - auth.admin.delete_user()는 service_role 키가 필요하여 서버에서만 처리
    - 클라이언트에서 직접 호출 불가
    - 동기 Supabase 클라이언트 사용으로 동기 핸들러로 정의
    """
    user_id = auth_user.id

    # 1. auth.users에서 먼저 삭제 (Admin API)
    # auth.users 삭제 시 ON DELETE CASCADE가 설정되어 있으면 public.users도 자동 삭제됨
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception:
        logger.exception("Failed to delete auth user: user_id=%s", user_id)
        raise HTTPException(
            status_code=500, detail="Failed to delete auth user"
        )

    # 2. public.users에서 삭제 (CASCADE가 없는 경우를 대비)
    # 네트워크/타임아웃/RLS 등 런타임 예외 처리
    try:
        response = supabase.table("users").delete().eq("id", user_id).execute()
    except Exception as err:
        logger.error("Failed deleting public.users for user_id=%s: %s", user_id, err)
        raise HTTPException(
            status_code=500, detail="Failed to delete user data"
        )

    # PostgREST 응답 에러 확인
    if hasattr(response, "error") and response.error:
        logger.error(
            "DB error deleting public.users for user_id=%s: %s",
            user_id,
            response.error,
        )
        raise HTTPException(
            status_code=500, detail="Failed to delete user data"
        )

    # data가 빈 리스트면 이미 삭제된 것으로 간주 (CASCADE)
    if not response.data:
        logger.warning(
            "public.users row not found (may already be deleted by CASCADE): user_id=%s",
            user_id,
        )

    return {"message": "Account deleted"}
