from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import supabase

security = HTTPBearer()


def get_auth_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """토큰 검증 후 user 반환"""
    
    token = credentials.credentials
    
    try:
        response = supabase.auth.get_user(token)
        return response.user
    except Exception as e:
         # logger.error(f"Auth failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")