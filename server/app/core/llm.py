"""LLM 인스턴스 팩토리

앱 전체에서 공통으로 사용하는 LLM 인스턴스를 제공합니다.
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import settings


@lru_cache
def get_llm(
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """기본 LLM 인스턴스 (복잡한 추론, 분석용)

    Args:
        temperature: 생성 다양성 (기본값: 0.1, 결정적 출력)
        max_tokens: 최대 출력 토큰 수 (기본값: None, 모델 기본값 사용)

    Returns:
        ChatOpenAI 인스턴스
    """
    kwargs: dict = {
        "model": settings.LLM_MODEL,
        "temperature": temperature,
        "api_key": settings.OPENAI_API_KEY,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


@lru_cache
def get_fast_llm(temperature: float = 0.3) -> ChatOpenAI:
    """빠른 LLM 인스턴스 (간단한 작업, 비용 효율)

    gpt-4o-mini 사용으로 빠르고 저렴한 응답.
    설명 생성, 요약 등 복잡한 추론이 필요없는 작업에 적합.

    Args:
        temperature: 생성 다양성 (기본값: 0.3, 약간의 다양성)

    Returns:
        ChatOpenAI 인스턴스
    """
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
    )
