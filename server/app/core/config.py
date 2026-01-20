from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env에 정의되지 않은 변수 무시
    )


settings = Settings()
