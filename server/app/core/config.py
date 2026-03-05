import re

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    TAVILY_API_KEY: str
    UPSTAGE_API_KEY: str | None = None  # Upstage Solar Embedding용
    CORS_ORIGINS: str = ""
    CORS_ORIGIN_REGEX: str | None = None  # Preview 도메인용 정규식 패턴

    @field_validator("CORS_ORIGIN_REGEX")
    @classmethod
    def validate_cors_origin_regex(cls, v: str | None) -> str | None:
        """CORS_ORIGIN_REGEX가 유효한 정규식인지 검증"""
        if v is None or v == "":
            return None
        try:
            re.compile(v)
            return v
        except re.error as e:
            raise ValueError(f"CORS_ORIGIN_REGEX가 유효한 정규식이 아닙니다: '{v}'. " f"오류: {e.msg}") from e

    # 디버그 설정
    ENABLE_DEBUG_PII_LOGS: bool = True

    # 법령 API 설정
    LAW_API_BASE_URL: str
    LAW_API_OC: str

    # Vector DB 설정
    VECTORDB_TYPE: str = "chroma"  # chroma | qdrant
    CHROMA_MODE: str = "persistent"  # persistent | http | ephemeral
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIR: str = "./data/chroma"  # persistent 모드 시 사용
    # Qdrant 설정
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None  # Cloud 사용 시 필요

    # LLM 설정
    LLM_MODEL: str
    LLM_EMBEDDING_MODEL: str

    # Google Drive 설정 (RAG 데이터 다운로드용)
    GOOGLE_DRIVE_URL: str = "https://drive.google.com/drive/folders/"
    R1_DATA_ID: str | None = None
    R2_DATA_ID: str | None = None
    DRAFT_TEMPLATE_FASTCHECK_ID: str | None = None
    DRAFT_TEMPLATE_TEMPORARY_ID: str | None = None
    DRAFT_TEMPLATE_DEMONSTRATION_ID: str | None = None

    # Supabase 설정 (pydantic 필드로 변경)
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env에 정의되지 않은 변수 무시
    )


settings = Settings()

# settings 생성 후에 supabase 클라이언트 만들기
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
