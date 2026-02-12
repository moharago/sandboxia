"""Vector DB 추상화 레이어

VectorStore 교체 시 구현체만 변경하면 됩니다.
현재 구현: ChromaDB (모드별 분기)

CHROMA_MODE:
- persistent: 로컬 파일 기반 (개발용, Docker 불필요)
- http: HTTP 클라이언트 (운영용, ChromaDB 서버 필요)
- ephemeral: 인메모리 (테스트용)
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

import chromadb
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.rag.config import EmbeddingConfig

logger = logging.getLogger(__name__)


class ChromaMode(str, Enum):
    """ChromaDB 연결 모드"""

    PERSISTENT = "persistent"  # 로컬 파일 기반
    HTTP = "http"  # HTTP 클라이언트 (서버 연결)
    EPHEMERAL = "ephemeral"  # 인메모리 (테스트용)


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


def _create_chroma_client() -> chromadb.ClientAPI:
    """ChromaDB 클라이언트 생성 (모드별 분기)

    Returns:
        ChromaDB 클라이언트

    Raises:
        ConnectionError: HTTP 모드에서 연결 실패 시
        ValueError: 알 수 없는 모드
    """
    mode = settings.CHROMA_MODE.lower()

    if mode == ChromaMode.PERSISTENT:
        # 로컬 파일 기반 (Docker 불필요)
        logger.info(f"ChromaDB persistent 모드: {settings.CHROMA_PERSIST_DIR}")
        return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

    elif mode == ChromaMode.EPHEMERAL:
        # 인메모리 (테스트용)
        logger.info("ChromaDB ephemeral 모드 (인메모리)")
        return chromadb.EphemeralClient()

    elif mode == ChromaMode.HTTP:
        # HTTP 클라이언트 (서버 연결)
        return _create_http_client_with_retry()

    else:
        raise ValueError(f"알 수 없는 CHROMA_MODE: {mode}. " f"사용 가능: persistent, http, ephemeral")


def _create_http_client_with_retry(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
) -> chromadb.ClientAPI:
    """ChromaDB HTTP 클라이언트 생성 (재시도 로직 포함)

    Args:
        max_retries: 최대 재시도 횟수
        initial_delay: 초기 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)

    Returns:
        ChromaDB 클라이언트

    Raises:
        ConnectionError: 모든 재시도 실패 시
    """
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
            # 연결 테스트
            client.heartbeat()
            logger.info(f"ChromaDB HTTP 모드 연결 성공: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"ChromaDB 연결 실패 (시도 {attempt + 1}/{max_retries}): {e}. " f"{delay:.1f}초 후 재시도..."
                )
                time.sleep(delay)
                delay = min(delay * 2, max_delay)  # 지수 백오프
            else:
                logger.error(f"ChromaDB 연결 실패: 모든 재시도 소진. 마지막 오류: {e}")
                raise ConnectionError(
                    f"ChromaDB 서버에 연결할 수 없습니다 " f"({settings.CHROMA_HOST}:{settings.CHROMA_PORT}): {e}"
                ) from e


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB 구현체 (모드별 분기 지원)"""

    def __init__(self, collection_name: str, embeddings: OpenAIEmbeddings):
        from langchain_chroma import Chroma

        self._collection_name = collection_name
        self._embeddings = embeddings

        # 모드별 ChromaDB 클라이언트 생성
        chroma_client = _create_chroma_client()

        self._client = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embeddings,
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

        return [SearchResult(document=doc, score=score) for doc, score in docs_with_scores]

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

        return [SearchResult(document=doc, score=score) for doc, score in docs_with_scores]

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
# 임베딩 팩토리 함수
# =============================================================================


def create_embeddings(config: EmbeddingConfig) -> Embeddings:
    """EmbeddingConfig에 따라 적절한 임베딩 모델 반환

    Args:
        config: 임베딩 설정 (provider, model 등)

    Returns:
        Embeddings 인스턴스

    Raises:
        ValueError: 지원하지 않는 provider
        RuntimeError: API 키 미설정
    """
    provider = config.provider.lower()

    if provider == "openai":
        return OpenAIEmbeddings(
            model=config.model,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    elif provider == "upstage":
        if not settings.UPSTAGE_API_KEY:
            raise RuntimeError(
                "Upstage 임베딩을 사용하려면 .env에 UPSTAGE_API_KEY를 설정하세요.\n"
                "API 키는 https://console.upstage.ai 에서 발급받을 수 있습니다."
            )
        from langchain_upstage import UpstageEmbeddings

        return UpstageEmbeddings(
            model=config.model,
            api_key=settings.UPSTAGE_API_KEY,
        )

    elif provider == "local":
        # 디바이스 자동 감지: CUDA > MPS (Apple Silicon) > CPU
        import torch
        from langchain_huggingface import HuggingFaceEmbeddings

        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

        logger.info(f"로컬 임베딩 모델 '{config.model}' 사용 (device: {device})")

        model_kwargs = {
            "device": device,
            "trust_remote_code": True,  # KURE 등 일부 모델 필요
        }
        encode_kwargs = {
            "normalize_embeddings": True,  # 코사인 유사도용 정규화
            "batch_size": 32,
            "show_progress_bar": False,
        }

        return HuggingFaceEmbeddings(
            model_name=config.model,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
        )

    else:
        raise ValueError(f"알 수 없는 임베딩 provider: '{provider}'. " "지원: openai, upstage, local")


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """임베딩 모델 인스턴스 반환 (기본값: .env의 LLM_EMBEDDING_MODEL)"""
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
