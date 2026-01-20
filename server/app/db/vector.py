"""Vector DB 클라이언트"""

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """임베딩 모델 인스턴스 반환"""
    return OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )


@lru_cache
def get_vectorstore(collection_name: str = "domain_laws") -> Chroma:
    """Vector Store 인스턴스 반환

    Args:
        collection_name: 컬렉션 이름

    Returns:
        Chroma Vector Store 인스턴스
    """
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )


def get_domain_law_retriever(
    domain: str | None = None,
    top_k: int = 5,
) -> VectorStoreRetriever:
    """도메인별 법령 검색 리트리버 반환

    Args:
        domain: 도메인 필터 (healthcare, finance, data, privacy, telecom)
        top_k: 반환할 결과 수

    Returns:
        VectorStoreRetriever 인스턴스
    """
    vectorstore = get_vectorstore("domain_laws")

    search_kwargs = {"k": top_k}
    if domain:
        search_kwargs["filter"] = {"domain": domain}

    return vectorstore.as_retriever(search_kwargs=search_kwargs)
