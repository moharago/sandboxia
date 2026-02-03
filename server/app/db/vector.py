"""Vector DB 추상화 레이어

VectorStore 교체 시 구현체만 변경하면 됩니다.
현재 구현: ChromaDB
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

# =============================================================================
# 검색 결과 타입
# =============================================================================


@dataclass
class SearchResult:
    """벡터 검색 결과"""

    document: Document
    score: float  # 0~1 정규화 (높을수록 유사)

    @property
    def content(self) -> str:
        return self.document.page_content

    @property
    def metadata(self) -> dict[str, Any]:
        return self.document.metadata


# =============================================================================
# 추상 인터페이스
# =============================================================================


class BaseVectorStore(ABC):
    """VectorStore 추상 베이스 클래스

    새로운 VectorDB 추가 시 이 클래스를 상속하여 구현합니다.
    """

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (점수 포함)

        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            filter: 메타데이터 필터

        Returns:
            검색 결과 리스트 (점수 0~1 정규화, 높을수록 유사)
        """
        pass

    @abstractmethod
    def add_documents(
        self,
        documents: list[Document],
        ids: list[str] | None = None,
    ) -> list[str]:
        """문서 추가

        Args:
            documents: 추가할 문서 리스트
            ids: 문서 ID 리스트 (없으면 자동 생성)

        Returns:
            추가된 문서 ID 리스트
        """
        pass

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """문서 삭제

        Args:
            ids: 삭제할 문서 ID 리스트
        """
        pass


# =============================================================================
# ChromaDB 구현체
# =============================================================================


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB 구현체"""

    def __init__(self, collection_name: str, embeddings: OpenAIEmbeddings):
        from langchain_chroma import Chroma

        self._collection_name = collection_name
        self._embeddings = embeddings
        self._client = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (relevance score 사용)"""
        search_kwargs: dict[str, Any] = {"k": k}
        if filter:
            search_kwargs["filter"] = filter

        # relevance_scores: 0~1 범위, 높을수록 유사
        docs_with_scores = self._client.similarity_search_with_relevance_scores(
            query,
            **search_kwargs,
        )

        return [
            SearchResult(document=doc, score=score) for doc, score in docs_with_scores
        ]

    def similarity_search_with_distance(
        self,
        query: str,
        k: int = 5,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (distance score 사용, 낮을수록 유사)

        일부 사용처에서 distance 기반 점수가 필요한 경우 사용.
        반환되는 score는 distance 값 그대로입니다.
        """
        search_kwargs: dict[str, Any] = {"k": k}
        if filter:
            search_kwargs["filter"] = filter

        docs_with_scores = self._client.similarity_search_with_score(
            query,
            **search_kwargs,
        )

        return [
            SearchResult(document=doc, score=score) for doc, score in docs_with_scores
        ]

    def add_documents(
        self,
        documents: list[Document],
        ids: list[str] | None = None,
    ) -> list[str]:
        """문서 추가"""
        return self._client.add_documents(documents, ids=ids)

    def delete(self, ids: list[str]) -> None:
        """문서 삭제"""
        self._client.delete(ids=ids)


# =============================================================================
# 팩토리 함수
# =============================================================================


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """임베딩 모델 인스턴스 반환"""
    return OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )


# 컬렉션별 VectorStore 캐시
_vectorstore_cache: dict[str, BaseVectorStore] = {}


def get_vector_store(collection_name: str) -> BaseVectorStore:
    """VectorStore 인스턴스 반환

    Args:
        collection_name: 컬렉션 이름

    Returns:
        VectorStore 인스턴스 (현재: ChromaDB)
    """
    if collection_name not in _vectorstore_cache:
        _vectorstore_cache[collection_name] = ChromaVectorStore(
            collection_name=collection_name,
            embeddings=get_embeddings(),
        )
    return _vectorstore_cache[collection_name]
