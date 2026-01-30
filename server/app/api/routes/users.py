from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_auth_user
from app.core.config import supabase

router = APIRouter()


# ================================
# 유저 삭제 (service_role 필요)
# ================================
@router.delete("/users/me")
async def delete_user(auth_user=Depends(get_auth_user)):
    """본인 계정 삭제

    - auth.admin.delete_user()는 service_role 키가 필요하여 서버에서만 처리
    - 클라이언트에서 직접 호출 불가
    """

    # 1. auth.users에서 먼저 삭제 (Admin API)
    # auth.users 삭제 시 ON DELETE CASCADE가 설정되어 있으면 public.users도 자동 삭제됨
    try:
        supabase.auth.admin.delete_user(auth_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete auth user: {str(e)}"
        )

    # 2. public.users에서 삭제 (CASCADE가 없는 경우를 대비)
    try:
        supabase.table("users").delete().eq("id", auth_user.id).execute()
    except Exception as e:
        # auth.users는 이미 삭제됨, public.users 삭제 실패는 로깅만
        # CASCADE가 이미 처리했을 수 있음
        print(
            f"Warning: Failed to delete public.users row (may already be deleted by CASCADE): {str(e)}"
        )

    return {"message": "Account deleted"}
