"""R1 규제제도 & 절차 RAG 평가 공통 모듈

run_evaluation.py와 run_llm_evaluation.py에서 공유하는 함수들.

주요 기능:
- 평가셋 로드
- Vector Store 연결
- Hybrid Retriever (BM25 + Vector)
- Gold chunk ID 매칭 (chunk_id 기반)
- Retrieval 지표 계산
"""

import json
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_REGULATIONS
from app.db.vector import create_embeddings
from app.rag.config import EmbeddingConfig
from eval.metrics import RetrievalMetrics

# 경로 설정
EVAL_DIR = Path(__file__).parent
EVALUATION_SET_PATH = EVAL_DIR / "datasets" / "evaluation_set.json"
RESULTS_DIR_RETRIEVAL = EVAL_DIR / "results" / "retrieval"
RESULTS_DIR_LLM = EVAL_DIR / "results" / "llm"
R1_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "r1_data" / "r1_rag_ict_only.json"


def load_evaluation_set() -> dict:
    """평가셋 로드"""
    with open(EVALUATION_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_vector_store(
    embedding_config: EmbeddingConfig | None = None,
    collection_suffix: str = "",
) -> Chroma:
    """Vector Store 연결

    기존 Vector Store에 연결하여 검색 수행.
    쿼리 임베딩을 위해 embedding_function이 필요함.

    Args:
        embedding_config: 임베딩 설정 (None이면 .env의 LLM_EMBEDDING_MODEL 사용)
        collection_suffix: 컬렉션 이름에 붙일 접미사

    Returns:
        Chroma Vector Store
    """
    if embedding_config is None:
        # 프리셋 없으면 .env의 LLM_EMBEDDING_MODEL 사용
        embeddings = OpenAIEmbeddings(
            model=settings.LLM_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    else:
        # 프리셋 있으면 프리셋 사용
        embeddings = create_embeddings(embedding_config)

    collection_name = COLLECTION_REGULATIONS + collection_suffix

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.CHROMA_PERSIST_DIR),
    )


def build_gold_chunk_ids(
    gold_chunks: list[dict],
) -> tuple[list[str], list[str]]:
    """gold_chunks에서 매칭용 ID 생성

    R1은 직접 chunk_id로 매칭 (R3와 달리 조 단위 매칭 불필요)

    Returns:
        (all_gold_ids, must_have_ids)
    """
    all_ids = []
    must_have_ids = []

    for chunk in gold_chunks:
        chunk_id = chunk.get("chunk_id", "")
        all_ids.append(chunk_id)

        if chunk.get("must_have", False):
            must_have_ids.append(chunk_id)

    return all_ids, must_have_ids


def extract_chunk_id_from_doc(doc) -> str:
    """Document에서 chunk_id 추출

    ChromaDB에는 document_id (예: r1-007)로 저장되어 있지만,
    평가셋은 chunk_id 형식 (예: reg_r1-007)을 사용하므로
    prefix를 추가하여 매칭
    """
    doc_id = doc.metadata.get("document_id", "")
    if doc_id:
        return f"reg_{doc_id}"
    return ""


def calculate_retrieval_metrics(
    retrieved_ids: list[str],
    gold_ids: list[str],
    must_have_ids: list[str],
    k: int,
) -> RetrievalMetrics:
    """Retrieval 지표 계산

    Args:
        retrieved_ids: 검색된 청크 ID 목록
        gold_ids: 전체 정답 청크 ID 목록
        must_have_ids: 핵심 정답 청크 ID 목록
        k: Top-K 값

    Returns:
        RetrievalMetrics 객체
    """
    top_k_retrieved = retrieved_ids[:k]
    top_k_set = set(top_k_retrieved)

    # Recall@K: gold 중 Top-K에서 매칭된 비율
    if not gold_ids:
        recall = 1.0
        retrieved_gold = 0
    else:
        matched_gold = len(set(gold_ids) & top_k_set)
        recall = matched_gold / len(gold_ids)
        retrieved_gold = matched_gold

    # Must-Have Recall@K
    if not must_have_ids:
        must_have_recall = 1.0
        retrieved_must_have = 0
    else:
        matched_must_have = len(set(must_have_ids) & top_k_set)
        must_have_recall = matched_must_have / len(must_have_ids)
        retrieved_must_have = matched_must_have

    # MRR: 첫 번째 정답의 역순위
    mrr = 0.0
    first_hit_rank = None
    gold_set = set(gold_ids)
    for rank, ret_id in enumerate(retrieved_ids, start=1):
        if ret_id in gold_set:
            mrr = 1.0 / rank
            first_hit_rank = rank
            break

    return RetrievalMetrics(
        recall_at_k=recall,
        must_have_recall_at_k=must_have_recall,
        mrr=mrr,
        k=k,
        total_gold=len(gold_ids),
        retrieved_gold=retrieved_gold,
        total_must_have=len(must_have_ids),
        retrieved_must_have=retrieved_must_have,
        first_hit_rank=first_hit_rank,
    )


def get_chunk_statistics(vector_store: Chroma) -> dict:
    """Vector Store에서 청크 통계 조회

    Returns:
        {
            "total_chunks": int,
            "avg_chunk_length": float,
        }
    """
    result = vector_store.get(include=["documents"])

    documents = result.get("documents", [])
    filtered_documents = [doc for doc in documents if doc]
    total_chunks = len(filtered_documents)

    if total_chunks == 0:
        return {
            "total_chunks": 0,
            "avg_chunk_length": 0.0,
        }

    total_length = sum(len(doc) for doc in filtered_documents)
    avg_length = total_length / total_chunks

    return {
        "total_chunks": total_chunks,
        "avg_chunk_length": round(avg_length, 1),
    }


def load_r1_documents() -> list[Document]:
    """R1 RAG 문서 로드 (BM25용)

    Returns:
        LangChain Document 리스트
    """
    with open(R1_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for item in data:
        # title + content 결합
        text = f"{item.get('title', '')}\n\n{item.get('content', '')}"
        doc = Document(
            page_content=text,
            metadata={
                "document_id": item.get("id", ""),
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "track": item.get("track", ""),
            },
        )
        documents.append(doc)

    return documents


class HybridRetriever:
    """Hybrid Retriever (BM25 + Vector) with RRF

    Reciprocal Rank Fusion으로 두 검색 결과를 결합합니다.
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_store: Chroma,
        vector_weight: float = 0.5,
        k: int = 5,
        rrf_k: int = 60,
    ):
        self.bm25_retriever = bm25_retriever
        self.vector_store = vector_store
        self.vector_weight = vector_weight
        self.bm25_weight = 1.0 - vector_weight
        self.k = k
        self.rrf_k = rrf_k  # RRF 상수

    def invoke(self, query: str) -> list[Document]:
        """Hybrid 검색 실행

        Args:
            query: 검색 쿼리

        Returns:
            RRF로 결합된 Document 리스트
        """
        # 1. BM25 검색
        bm25_results = self.bm25_retriever.invoke(query)

        # 2. Vector 검색
        vector_results = self.vector_store.similarity_search(query, k=self.k * 2)

        # 3. RRF 점수 계산
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        # BM25 결과 점수
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.metadata.get("document_id", doc.page_content[:50])
            rrf_score = self.bm25_weight / (self.rrf_k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            doc_map[doc_id] = doc

        # Vector 결과 점수
        for rank, doc in enumerate(vector_results):
            doc_id = doc.metadata.get("document_id", doc.page_content[:50])
            rrf_score = self.vector_weight / (self.rrf_k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # 4. 점수로 정렬
        sorted_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

        # 5. 상위 K개 반환
        return [doc_map[doc_id] for doc_id in sorted_ids[: self.k]]


def get_hybrid_retriever(
    embedding_config: EmbeddingConfig | None = None,
    collection_suffix: str = "",
    vector_weight: float = 0.5,
    k: int = 5,
) -> HybridRetriever:
    """Hybrid Retriever 생성 (BM25 + Vector)

    Args:
        embedding_config: 임베딩 설정
        collection_suffix: 컬렉션 접미사
        vector_weight: 벡터 검색 가중치 (0.0~1.0, 나머지는 BM25)
        k: Top-K 값

    Returns:
        HybridRetriever (BM25 + Vector 조합)
    """
    # 1. Vector Store
    vector_store = get_vector_store(embedding_config, collection_suffix)

    # 2. BM25 Retriever
    documents = load_r1_documents()
    bm25_retriever = BM25Retriever.from_documents(documents, k=k * 2)

    # 3. Hybrid Retriever
    return HybridRetriever(
        bm25_retriever=bm25_retriever,
        vector_store=vector_store,
        vector_weight=vector_weight,
        k=k,
    )
