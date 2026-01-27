from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.config import supabase
from app.api.deps import get_auth_user

router = APIRouter()


# ================================
# 요청 모델
# ================================
# class UserCreate(BaseModel):
#     name: str         # 담당자명
#     company: str      # 회사명
#     phone: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None 


# Google 로그인 트리거로 자동 생성하므로 삭제(임시 주석 처리)
# ================================
# 회원가입 
# ================================
# @router.post("/users/signup")
# async def create_user(
#     user: UserCreate,
#     auth_user = Depends(get_auth_user),
# ):
#     """Supabase Auth 회원가입 후 추가 정보 저장"""
    
#     existing = supabase.table("users")\
#         .select("id")\
#         .eq("id", auth_user.id)\
#         .execute()

#     if existing.data:
#         raise HTTPException(status_code=400, detail="User already exists")

#     result = supabase.table("users").insert({
#         "id": auth_user.id,
#         "email": auth_user.email,
#         "name": user.name,
#         "company": user.company,
#         "phone": user.phone
#     }).execute()

#     return result.data[0]


# ================================
# 유저 조회
# ================================
@router.get("/users/me")
async def get_user(auth_user = Depends(get_auth_user)):
    """본인 정보 조회"""

    try:
        result = supabase.table("users")\
            .select("*")\
            .eq("id", auth_user.id)\
            .single()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")

        return result.data
    except HTTPException:
        raise
    except Exception as e:
        # single()이 행이 없거나 여러 행일 때 예외 발생
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")


# ================================
# 유저 정보 수정
# ================================
@router.patch("/users/me")
async def update_user(
    payload: UserUpdate,
    auth_user = Depends(get_auth_user),       
):
    """본인 정보 수정 및 상태 변경"""
    
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = supabase.table("users")\
        .update(update_data)\
        .eq("id", auth_user.id)\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    return result.data

# ================================
# 유저 삭제
# ================================
@router.delete("/users/me")
async def delete_user(auth_user = Depends(get_auth_user)):
    """본인 계정 삭제"""

    # 1. auth.users에서 먼저 삭제 (Admin API)
    # auth.users 삭제 시 ON DELETE CASCADE가 설정되어 있으면 public.users도 자동 삭제됨
    try:
        supabase.auth.admin.delete_user(auth_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete auth user: {str(e)}"
        )

    # 2. public.users에서 삭제 (CASCADE가 없는 경우를 대비)
    try:
        supabase.table("users")\
            .delete()\
            .eq("id", auth_user.id)\
            .execute()
    except Exception as e:
        # auth.users는 이미 삭제됨, public.users 삭제 실패는 로깅만
        # CASCADE가 이미 처리했을 수 있음
        print(f"Warning: Failed to delete public.users row (may already be deleted by CASCADE): {str(e)}")

    return {"message": "Account deleted"}
