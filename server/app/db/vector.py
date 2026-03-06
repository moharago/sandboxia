"""Vector DB 추상화 레이어

VectorStore 교체 시 구현체만 변경하면 됩니다.
현재 구현: ChromaDB, Qdrant

CHROMA_MODE:
- persistent: 로컬 파일 기반 (개발용, Docker 불필요)
- http: HTTP 클라이언트 (운영용, ChromaDB 서버 필요)
- ephemeral: 인메모리 (테스트용)

Hybrid Search:
- Dense (벡터 유사도) + Sparse (BM25 키워드) 조합
- alpha: Dense 가중치 (0.0 = BM25만, 1.0 = Dense만, 0.7 = 기본)
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Union

import chromadb
from chromadb.api import ClientAPI
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.rag.config import EmbeddingConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Enum & Config
# =============================================================================


class VectorDBType(str, Enum):
    """Vector DB 타입"""

    CHROMA = "chroma"
    QDRANT = "qdrant"


class ChromaMode(str, Enum):
    """ChromaDB 연결 모드"""

    PERSISTENT = "persistent"  # 로컬 파일 기반
    HTTP = "http"  # HTTP 클라이언트 (서버 연결)
    EPHEMERAL = "ephemeral"  # 인메모리 (테스트용)


@dataclass
class HybridSearchConfig:
    """Hybrid Search 설정

    Attributes:
        enabled: Hybrid Search 활성화 여부
        alpha: Dense 가중치 (0.0~1.0, 기본 0.7)
               0.0 = Sparse(BM25)만, 1.0 = Dense만
        sparse_model: Sparse 임베딩 모델 (Qdrant용)
    """

    enabled: bool = False
    alpha: float = 0.7  # Dense 70%, Sparse 30%
    sparse_model: str = "prithivida/Splade_PP_en_v1"  # H3: SPLADE (평가 채택)


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
# DB-agnostic 필터 타입
# =============================================================================


@dataclass(frozen=True)
class Eq:
    """field == value"""

    field: str
    value: str


@dataclass(frozen=True)
class Or:
    """조건 중 하나라도 참"""

    conditions: tuple["FilterExpr", ...]

    def __init__(self, *conditions: "FilterExpr"):
        object.__setattr__(self, "conditions", conditions)


@dataclass(frozen=True)
class And:
    """조건 모두 참"""

    conditions: tuple["FilterExpr", ...]

    def __init__(self, *conditions: "FilterExpr"):
        object.__setattr__(self, "conditions", conditions)


FilterExpr = Union[Eq, Or, And]


# =============================================================================
# 추상 인터페이스
# =============================================================================


class BaseVectorStore(ABC):
    """VectorStore 추상 베이스 클래스

    새로운 VectorDB 추가 시 이 클래스를 상속하여 구현합니다.
    """

    # Hybrid Search 설정 (서브클래스에서 설정)
    _hybrid_config: HybridSearchConfig = field(default_factory=HybridSearchConfig)

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: FilterExpr | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (Dense only)

        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            filter: 메타데이터 필터

        Returns:
            검색 결과 리스트 (점수 0~1 정규화, 높을수록 유사)
        """
        pass

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        filter: FilterExpr | None = None,
        alpha: float | None = None,
    ) -> list[SearchResult]:
        """Hybrid Search (Dense + Sparse)

        기본 구현은 similarity_search로 fallback.
        서브클래스에서 오버라이드하여 실제 Hybrid 구현.

        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            filter: 메타데이터 필터
            alpha: Dense 가중치 (None이면 config 값 사용)

        Returns:
            검색 결과 리스트
        """
        # 기본 구현: Dense only (fallback)
        logger.debug("hybrid_search fallback to similarity_search (Dense only)")
        return self.similarity_search(query, k, filter)

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

    def delete_collection(self) -> None:
        """컬렉션 삭제 (선택적 구현)"""
        logger.warning(f"delete_collection not implemented for {self.__class__.__name__}")


# =============================================================================
# ChromaDB 구현체
# =============================================================================


def _create_chroma_client() -> ClientAPI:
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
) -> ClientAPI:
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
    """ChromaDB 구현체 (모드별 분기 지원)

    Note: Chroma는 네이티브 Hybrid Search를 지원하지 않습니다.
    hybrid_search 호출 시 Dense Search로 fallback됩니다.
    """

    def __init__(
        self,
        collection_name: str,
        embeddings: Embeddings,
        hybrid_config: HybridSearchConfig | None = None,
    ):
        from langchain_chroma import Chroma

        self._collection_name = collection_name
        self._embeddings = embeddings
        self._hybrid_config = hybrid_config or HybridSearchConfig()

        # 모드별 ChromaDB 클라이언트 생성
        chroma_client = _create_chroma_client()

        self._client = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )

    @staticmethod
    def _to_chroma_filter(expr: FilterExpr) -> dict[str, Any]:
        """FilterExpr → ChromaDB 네이티브 필터 변환"""
        if isinstance(expr, Eq):
            return {expr.field: {"$eq": expr.value}}
        if isinstance(expr, Or):
            return {"$or": [ChromaVectorStore._to_chroma_filter(c) for c in expr.conditions]}
        if isinstance(expr, And):
            return {"$and": [ChromaVectorStore._to_chroma_filter(c) for c in expr.conditions]}
        raise TypeError(f"Unknown filter type: {type(expr)}")

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: FilterExpr | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (relevance score 사용)"""
        search_kwargs: dict[str, Any] = {"k": k}
        if filter:
            search_kwargs["filter"] = self._to_chroma_filter(filter)

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
        filter: FilterExpr | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (distance score 사용, 낮을수록 유사)

        일부 사용처에서 distance 기반 점수가 필요한 경우 사용.
        반환되는 score는 distance 값 그대로입니다.
        """
        search_kwargs: dict[str, Any] = {"k": k}
        if filter:
            search_kwargs["filter"] = self._to_chroma_filter(filter)

        docs_with_scores = self._client.similarity_search_with_score(
            query,
            **search_kwargs,
        )

        return [SearchResult(document=doc, score=score) for doc, score in docs_with_scores]

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        filter: FilterExpr | None = None,
        alpha: float | None = None,
    ) -> list[SearchResult]:
        """Hybrid Search (Chroma는 Dense only)

        Chroma는 네이티브 Sparse/BM25를 지원하지 않아 Dense 검색만 수행.
        Hybrid Search가 필요하면 Qdrant 사용을 권장.
        """
        if self._hybrid_config.enabled:
            logger.warning(
                "ChromaDB는 네이티브 Hybrid Search를 지원하지 않습니다. "
                "Dense Search만 수행합니다. Hybrid가 필요하면 Qdrant를 사용하세요."
            )
        return self.similarity_search(query, k, filter)

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

    def delete_collection(self) -> None:
        """컬렉션 삭제"""
        try:
            chroma_client = _create_chroma_client()
            chroma_client.delete_collection(name=self._collection_name)
            logger.info(f"Chroma 컬렉션 '{self._collection_name}' 삭제 완료")
        except ValueError:
            logger.warning(f"Chroma 컬렉션 '{self._collection_name}' 없음")


# =============================================================================
# Qdrant 구현체
# =============================================================================

# 로컬 모드 QdrantClient 싱글톤 (같은 디렉토리에 하나의 클라이언트만 허용)
_qdrant_local_client: Any = None
_qdrant_local_path: str | None = None
_qdrant_client_lock = threading.Lock()


def close_qdrant_client():
    """Qdrant 로컬 클라이언트 종료 및 lock 해제 (서버 shutdown 시 호출)"""
    global _qdrant_local_client, _qdrant_local_path
    with _qdrant_client_lock:
        if _qdrant_local_client is not None:
            try:
                _qdrant_local_client.close()
                logger.info("Qdrant embedded 클라이언트 종료 완료")
            except Exception as e:
                logger.warning(f"Qdrant 클라이언트 종료 중 오류: {e}")
            finally:
                _qdrant_local_client = None
                _qdrant_local_path = None


def _get_qdrant_client():
    """QdrantClient 인스턴스 반환 (로컬 모드에서는 싱글톤으로 재사용, 스레드 안전)"""
    global _qdrant_local_client, _qdrant_local_path
    from qdrant_client import QdrantClient

    if settings.QDRANT_API_KEY:
        logger.info(f"Qdrant Cloud 모드: {settings.QDRANT_HOST}")
        return QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=True,
        )
    elif getattr(settings, "QDRANT_MODE", "server") == "local":
        persist_dir = getattr(settings, "QDRANT_PERSIST_DIR", "./data/qdrant")
        # 빠른 경로: 이미 생성된 싱글톤 반환 (Lock 없이)
        if _qdrant_local_client is not None and _qdrant_local_path == persist_dir:
            return _qdrant_local_client
        # 느린 경로: Lock으로 스레드 안전하게 싱글톤 생성
        with _qdrant_client_lock:
            # Double-check: Lock 대기 중 다른 스레드가 생성했을 수 있음
            if _qdrant_local_client is not None and _qdrant_local_path == persist_dir:
                return _qdrant_local_client
            # stale lock 파일 제거 (이전 프로세스가 비정상 종료된 경우)
            import os

            lock_file = os.path.join(persist_dir, ".lock")
            if os.path.exists(lock_file):
                logger.warning(f"Qdrant stale lock 파일 제거: {lock_file}")
                os.remove(lock_file)
            logger.info(f"Qdrant embedded 모드 (로컬): {persist_dir}")
            _qdrant_local_client = QdrantClient(path=persist_dir)
            _qdrant_local_path = persist_dir
            return _qdrant_local_client
    else:
        logger.info(f"Qdrant 서버 모드: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant 구현체 (Docker/Cloud 지원, Hybrid Search 지원)

    Hybrid Search:
    - Dense: 전달받은 embeddings 사용
    - Sparse: FastEmbed SPLADE 모델 사용
    - alpha로 가중치 조절 (0.7 = Dense 70%, Sparse 30%)
    """

    def __init__(
        self,
        collection_name: str,
        embeddings: Embeddings,
        hybrid_config: HybridSearchConfig | None = None,
    ):
        from langchain_qdrant import QdrantVectorStore as LangchainQdrant
        from langchain_qdrant import RetrievalMode

        self._collection_name = collection_name
        self._embeddings = embeddings
        self._hybrid_config = hybrid_config or HybridSearchConfig()
        self._mode_lock = threading.Lock()

        # Qdrant 클라이언트 생성 (로컬 모드 싱글톤)
        client = _get_qdrant_client()

        self._qdrant_client = client

        # Hybrid Search용 Sparse Embedding (SPLADE/BM25)
        self._sparse_embeddings = None
        self._retrieval_mode = RetrievalMode.DENSE

        if self._hybrid_config.enabled:
            try:
                from langchain_qdrant import FastEmbedSparse

                self._sparse_embeddings = FastEmbedSparse(
                    model_name=self._hybrid_config.sparse_model
                )
                self._retrieval_mode = RetrievalMode.HYBRID
                logger.info(f"Qdrant Hybrid Search 활성화 (Sparse: {self._hybrid_config.sparse_model})")
            except ImportError:
                logger.warning(
                    "FastEmbedSparse를 사용할 수 없습니다. Dense Search만 사용합니다. "
                    "설치: uv sync (fastembed 포함)"
                )

        # 컬렉션 존재 여부 확인 및 생성
        self._ensure_collection_exists(embeddings)

        # LangChain Qdrant 래퍼 생성
        self._client = LangchainQdrant(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
            sparse_embedding=self._sparse_embeddings,
            retrieval_mode=self._retrieval_mode,
            validate_collection_config=False,
        )

    def _ensure_collection_exists(self, embeddings: Embeddings) -> None:
        """컬렉션이 없으면 자동 생성"""
        from qdrant_client.http import models

        try:
            self._qdrant_client.get_collection(self._collection_name)
            logger.debug(f"Qdrant 컬렉션 '{self._collection_name}' 존재 확인")
        except Exception:
            # 컬렉션이 없으면 새로 생성
            logger.info(f"Qdrant 컬렉션 '{self._collection_name}' 새로 생성 중...")

            # 임베딩 차원 확인 (샘플 텍스트로)
            sample_embedding = embeddings.embed_query("test")
            vector_size = len(sample_embedding)

            vectors_config = {
                "": models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                )
            }

            # Hybrid 모드면 Sparse 벡터도 추가
            sparse_vectors_config = None
            if self._sparse_embeddings is not None:
                sparse_vectors_config = {
                    "langchain-sparse": models.SparseVectorParams(
                        modifier=models.Modifier.IDF,
                    )
                }

            self._qdrant_client.create_collection(
                collection_name=self._collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            logger.info(f"Qdrant 컬렉션 '{self._collection_name}' 생성 완료")

    @staticmethod
    def _to_qdrant_filter(expr: FilterExpr):
        """FilterExpr → Qdrant 네이티브 필터 변환"""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        if isinstance(expr, Eq):
            return Filter(
                must=[FieldCondition(key=f"metadata.{expr.field}", match=MatchValue(value=expr.value))]
            )
        if isinstance(expr, Or):
            return Filter(should=[QdrantVectorStore._to_qdrant_filter(c) for c in expr.conditions])
        if isinstance(expr, And):
            return Filter(must=[QdrantVectorStore._to_qdrant_filter(c) for c in expr.conditions])
        raise TypeError(f"Unknown filter type: {type(expr)}")

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: FilterExpr | None = None,
    ) -> list[SearchResult]:
        """유사도 검색 (Dense only)"""
        from langchain_qdrant import RetrievalMode

        qdrant_filter = self._to_qdrant_filter(filter) if filter else None

        with self._mode_lock:
            original_mode = self._client.retrieval_mode
            self._client.retrieval_mode = RetrievalMode.DENSE
            try:
                docs_with_scores = self._client.similarity_search_with_score(
                    query,
                    k=k,
                    filter=qdrant_filter,
                )
            finally:
                self._client.retrieval_mode = original_mode

        return [SearchResult(document=doc, score=score) for doc, score in docs_with_scores]

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        filter: FilterExpr | None = None,
        alpha: float | None = None,
    ) -> list[SearchResult]:
        """Hybrid Search (Dense + Sparse)

        Args:
            query: 검색 쿼리
            k: 반환할 결과 수
            filter: 메타데이터 필터
            alpha: Dense 가중치 (0.0~1.0, None이면 config 값 사용)

        Returns:
            검색 결과 리스트 (RRF로 점수 조합)
        """
        if not self._hybrid_config.enabled or self._sparse_embeddings is None:
            logger.debug("Hybrid Search 비활성화, Dense Search로 fallback")
            return self.similarity_search(query, k, filter)

        from langchain_qdrant import RetrievalMode
        from qdrant_client.models import Rrf, RrfQuery

        qdrant_filter = self._to_qdrant_filter(filter) if filter else None

        # alpha 가중치 적용: Dense(alpha) + Sparse(1-alpha)
        effective_alpha = alpha if alpha is not None else self._hybrid_config.alpha
        rrf_query = RrfQuery(rrf=Rrf(weights=[effective_alpha, 1.0 - effective_alpha]))

        with self._mode_lock:
            original_mode = self._client.retrieval_mode
            self._client.retrieval_mode = RetrievalMode.HYBRID
            try:
                docs_with_scores = self._client.similarity_search_with_score(
                    query,
                    k=k,
                    filter=qdrant_filter,
                    hybrid_fusion=rrf_query,
                )
            finally:
                self._client.retrieval_mode = original_mode

        return [SearchResult(document=doc, score=score) for doc, score in docs_with_scores]

    def add_documents(
        self,
        documents: list[Document],
        ids: list[str] | None = None,
    ) -> list[str]:
        """문서 추가 (Hybrid 모드면 Sparse Vector도 함께 저장)

        Note:
            Qdrant는 UUID 또는 unsigned integer만 ID로 허용합니다.
            문자열 ID가 전달되면 UUID5로 변환합니다.
            원본 ID는 metadata['original_id']에 저장됩니다.
        """
        import uuid

        if ids:
            # 문자열 ID를 UUID5로 변환 (namespace + 원본 ID로 결정적 생성)
            uuid_ids = []
            for i, doc_id in enumerate(ids):
                # 원본 ID를 metadata에 보존
                if "original_id" not in documents[i].metadata:
                    documents[i].metadata["original_id"] = doc_id
                # UUID5 생성 (같은 ID는 항상 같은 UUID)
                uuid_ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id)))
            return self._client.add_documents(documents, ids=uuid_ids)
        return self._client.add_documents(documents, ids=ids)

    def delete(self, ids: list[str]) -> None:
        """문서 삭제"""
        self._client.delete(ids=ids)

    def delete_collection(self) -> None:
        """컬렉션 삭제"""
        try:
            self._qdrant_client.delete_collection(self._collection_name)
            logger.info(f"Qdrant 컬렉션 '{self._collection_name}' 삭제 완료")
        except Exception as e:
            logger.warning(f"Qdrant 컬렉션 삭제 실패: {e}")


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
        try:
            import torch
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as e:
            raise RuntimeError(
                "로컬 임베딩 모델을 사용하려면 추가 의존성이 필요합니다.\n"
                "설치: uv sync --group local-embeddings"
            ) from e

        # 디바이스 자동 감지: CUDA > MPS (Apple Silicon) > CPU
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
        }

        return HuggingFaceEmbeddings(
            model_name=config.model,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
            show_progress=False,
        )

    else:
        raise ValueError(f"알 수 없는 임베딩 provider: '{provider}'. " "지원: openai, upstage, local")


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """임베딩 모델 인스턴스 반환 (.env LLM_EMBEDDING_MODEL 사용)"""
    return OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )


# 컬렉션별 VectorStore 캐시
_vectorstore_cache: dict[str, BaseVectorStore] = {}
_vectorstore_cache_lock = threading.Lock()


def create_vector_store(
    collection_name: str,
    embeddings: Embeddings | None = None,
    vectordb_type: VectorDBType | str = VectorDBType.QDRANT,
    hybrid_config: HybridSearchConfig | None = None,
) -> BaseVectorStore:
    """VectorStore 인스턴스 생성 (Factory 함수)

    기본 동작 (Qdrant + E1 + H3):
    - 임베딩: text-embedding-3-large (3072차원)
    - Hybrid Search: SPLADE Dense 70% + Sparse 30%

    Args:
        collection_name: 컬렉션 이름
        embeddings: 임베딩 모델 (None이면 E1 사용)
        vectordb_type: Vector DB 타입 (기본: qdrant)
        hybrid_config: Hybrid Search 설정 (None이면 H3 사용)

    Returns:
        VectorStore 인스턴스

    Example:
        # 기본 (Qdrant + E1 + H3)
        store = create_vector_store("my_collection")

        # Chroma (Dense only)
        store = create_vector_store("my_collection", vectordb_type="chroma")
    """
    if embeddings is None:
        embeddings = get_embeddings()

    # 문자열을 Enum으로 변환
    if isinstance(vectordb_type, str):
        vectordb_type = VectorDBType(vectordb_type.lower())

    if vectordb_type == VectorDBType.QDRANT:
        # Qdrant: Dense only (Hybrid Search 비활성화 - 메모리 절약 + R1 평가 결과 Dense가 더 우수)
        if hybrid_config is None:
            hybrid_config = HybridSearchConfig(enabled=False)
        return QdrantVectorStore(
            collection_name=collection_name,
            embeddings=embeddings,
            hybrid_config=hybrid_config,
        )
    else:
        # Chroma: Dense only (Hybrid 미지원)
        if hybrid_config is None:
            hybrid_config = HybridSearchConfig(enabled=False)
        return ChromaVectorStore(
            collection_name=collection_name,
            embeddings=embeddings,
            hybrid_config=hybrid_config,
        )


def get_vector_store(
    collection_name: str,
    vectordb_type: VectorDBType | str = VectorDBType.QDRANT,
) -> BaseVectorStore:
    """VectorStore 인스턴스 반환 (캐시 사용)

    Args:
        collection_name: 컬렉션 이름
        vectordb_type: Vector DB 타입

    Returns:
        VectorStore 인스턴스 (캐시됨)
    """
    if isinstance(vectordb_type, str):
        vectordb_type = VectorDBType(vectordb_type.lower())
    cache_key = f"{vectordb_type.value}:{collection_name}"
    if cache_key in _vectorstore_cache:
        return _vectorstore_cache[cache_key]
    with _vectorstore_cache_lock:
        if cache_key not in _vectorstore_cache:
            _vectorstore_cache[cache_key] = create_vector_store(
                collection_name=collection_name,
                vectordb_type=vectordb_type,
            )
        return _vectorstore_cache[cache_key]
