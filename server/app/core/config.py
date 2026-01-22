from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client
import os

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    TAVILY_API_KEY: str
    CORS_ORIGINS: str = ""

    # 법령 API 설정
    LAW_API_BASE_URL: str
    LAW_API_OC: str

    # Vector DB 설정
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # LLM 설정
    LLM_MODEL: str
    LLM_EMBEDDING_MODEL: str

    # Google Drive 설정 (RAG 데이터 다운로드용)
    GOOGLE_DRIVE_URL: str = "https://drive.google.com/drive/folders/"
    R1_DATA_ID: str | None = None

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
