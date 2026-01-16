from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.sample import router as agent_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="MindBridge API", version="0.1.0")

    origins = [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
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

    app.include_router(agent_router)
    return app


app = create_app()
