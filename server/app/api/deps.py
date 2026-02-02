import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import supabase

security = HTTPBearer()


@dataclass
class MockUser:
    """개발 환경 테스트용 Mock User"""
    id: str
    email: str = "test@example.com"


def get_auth_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """토큰 검증 후 user 반환"""

    token = credentials.credentials

    # 개발 환경 테스트 모드 (DEV_MODE=true + token="test")
    if os.getenv("DEV_MODE") == "true" and token == "test":
        # 테스트 데이터의 user_id와 일치시킴
        return MockUser(id="84cce2dd-b855-4607-8761-2ef21c722e98")

    try:
        response = supabase.auth.get_user(token)
        return response.user
    except Exception:
         # logger.error(f"Auth failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")