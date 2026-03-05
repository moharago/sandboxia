"""
API Dependencies

인증 및 공통 의존성을 정의합니다.
"""

import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient, decode

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=True)

# JWKS 클라이언트 (ECC P-256 공개키 캐싱)
_jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwks_client = PyJWKClient(_jwks_url, cache_keys=True)


@dataclass
class AuthUser:
    """인증된 사용자 정보"""

    id: str
    email: str | None = None
    role: str | None = None


def get_auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthUser:
    """
    JWT 토큰을 JWKS로 검증하고 사용자 정보를 반환합니다.

    - Supabase JWKS 엔드포인트에서 공개키를 가져와 검증
    - CURRENT KEY와 PREVIOUS KEY 모두 자동 지원
    - 공개키는 캐시되어 성능 최적화

    Returns:
        AuthUser: 인증된 사용자 정보 (id, email, role)

    Raises:
        HTTPException 401: 토큰이 없거나, 만료되었거나, 유효하지 않은 경우
    """
    token = credentials.credentials

    try:
        # JWKS에서 토큰의 kid에 맞는 공개키 가져오기
        signing_key = _jwks_client.get_signing_key_from_jwt(token)

        # 토큰 검증 및 디코딩 (Supabase ECC P-256은 ES256 사용)
        payload = decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )

        # sub claim 검증 (필수)
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing required 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthUser(
            id=user_id,
            email=payload.get("email"),
            role=payload.get("role"),
        )

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        logger.exception("Invalid token error during authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.exception("Unexpected error during authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {type(e).__name__}: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
