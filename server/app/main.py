from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agents import router as agents_router
from app.api.routes.users import router as users_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="SandboxIA API",
        description="규제 샌드박스 컨설팅 AI 서비스 API",
        version="0.1.0",
    )

    origins = [
        origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()
    ]
    if not origins:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(agents_router, prefix="/api/v1", tags=["AI Agents"])
    app.include_router(users_router, prefix="/api", tags=["Users"])

    return app


app = create_app()


@app.get("/")
async def root():
    return {"message": "SandboxIA API 서버 실행 중"}


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (Docker, 로드밸런서용)"""
    return {"status": "healthy"}
