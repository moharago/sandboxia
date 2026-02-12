"""R3 법령 RAG 평가 공통 모듈

run_evaluation.py와 run_llm_evaluation.py에서 공유하는 함수들.

주요 기능:
- 평가셋 로드
- Vector Store 연결
- Gold chunk ID 생성 및 매칭 (조 단위 - 청킹 전략 무관)
- Retrieval 지표 계산
"""

import json
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from app.db.vector import create_embeddings
from app.rag.config import EmbeddingConfig
from eval.metrics import RetrievalMetrics

# 경로 설정
EVAL_DIR = Path(__file__).parent
EVALUATION_SET_PATH = EVAL_DIR / "datasets" / "evaluation_set.json"
RESULTS_DIR_RETRIEVAL = EVAL_DIR / "results" / "retrieval"
RESULTS_DIR_LLM = EVAL_DIR / "results" / "llm"


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

    collection_name = COLLECTION_LAWS + collection_suffix

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(settings.CHROMA_PERSIST_DIR),
    )


def build_gold_chunk_ids(
    gold_citations: list[dict],
) -> tuple[list[dict], list[dict]]:
    """gold_citations에서 매칭용 ID 생성

    매칭 키: (law_name, article_no) - 조 단위 매칭 (청킹 전략 무관)
    - article_title은 같은 조번호에 여러 조문이 있는 경우에만 구분용으로 사용

    Returns:
        (all_gold_ids, must_have_ids)
    """
    all_ids = []
    must_have_ids = []

    for citation in gold_citations:
        # 기본 매칭 키: law_name, article_no (조 단위)
        base_id = f"{citation.get('law_name', '')}|{citation.get('article_no', '')}"

        # article_title이 있으면 추가 (같은 조번호에 여러 조문이 있는 경우 구분)
        article_title = citation.get("article_title", "")

        gold_id = {
            "base_id": base_id,
            "article_title": article_title,
        }

        all_ids.append(gold_id)

        if citation.get("must_have", False):
            must_have_ids.append(gold_id)

    return all_ids, must_have_ids


def extract_chunk_id_from_doc(doc) -> dict:
    """Document에서 매칭용 chunk_id 추출 (조 단위)"""
    meta = doc.metadata
    # 조 단위 매칭 - paragraph_no 무시
    base_id = f"{meta.get('law_name', '')}|{meta.get('article_no', '')}"
    article_title = meta.get("article_title", "")

    return {
        "base_id": base_id,
        "article_title": article_title,
    }


def match_ids(retrieved_id: dict, gold_id: dict) -> bool:
    """두 ID가 매칭되는지 확인 (조 단위)

    매칭 규칙:
    1. base_id (law_name, article_no) 필수 일치 - 청킹 전략 무관
    2. gold_id에 article_title이 있으면 추가로 일치해야 함
    """
    if retrieved_id["base_id"] != gold_id["base_id"]:
        return False

    # gold에 article_title이 있으면 검증
    if gold_id["article_title"]:
        return retrieved_id["article_title"] == gold_id["article_title"]

    return True


def calculate_retrieval_metrics(
    retrieved_ids: list[dict],
    gold_ids: list[dict],
    must_have_ids: list[dict],
    k: int,
) -> RetrievalMetrics:
    """매칭 로직을 적용한 Retrieval 지표 계산

    Args:
        retrieved_ids: 검색된 청크 ID 목록
        gold_ids: 전체 정답 청크 ID 목록
        must_have_ids: 핵심 정답 청크 ID 목록
        k: Top-K 값

    Returns:
        RetrievalMetrics 객체
    """
    top_k_retrieved = retrieved_ids[:k]

    # Recall@K: gold 중 Top-K에서 매칭된 비율
    if not gold_ids:
        recall = 1.0
        retrieved_gold = 0
    else:
        matched_gold = 0
        for gold in gold_ids:
            for ret in top_k_retrieved:
                if match_ids(ret, gold):
                    matched_gold += 1
                    break
        recall = matched_gold / len(gold_ids)
        retrieved_gold = matched_gold

    # Must-Have Recall@K
    if not must_have_ids:
        must_have_recall = 1.0
        retrieved_must_have = 0
    else:
        matched_must_have = 0
        for gold in must_have_ids:
            for ret in top_k_retrieved:
                if match_ids(ret, gold):
                    matched_must_have += 1
                    break
        must_have_recall = matched_must_have / len(must_have_ids)
        retrieved_must_have = matched_must_have

    # MRR: 첫 번째 정답의 역순위
    mrr = 0.0
    first_hit_rank = None
    for rank, ret in enumerate(retrieved_ids, start=1):
        for gold in gold_ids:
            if match_ids(ret, gold):
                mrr = 1.0 / rank
                first_hit_rank = rank
                break
        if first_hit_rank:
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


def format_chunk_id(chunk_id: dict) -> str:
    """chunk_id를 읽기 쉬운 문자열로 변환"""
    if chunk_id["article_title"]:
        return f"{chunk_id['base_id']}|{chunk_id['article_title']}"
    return chunk_id["base_id"]


def format_chunk_ids(chunk_ids: list[dict]) -> list[str]:
    """chunk_id 목록을 읽기 쉬운 문자열 목록으로 변환"""
    return [format_chunk_id(cid) for cid in chunk_ids]


def get_chunk_statistics(vector_store: Chroma) -> dict:
    """Vector Store에서 청크 통계 조회

    Returns:
        {
            "total_chunks": int,
            "avg_chunk_length": float,
        }
    """
    # ChromaDB 공용 API를 사용하여 모든 문서 조회
    result = vector_store.get(include=["documents"])

    documents = result.get("documents", [])
    # None/empty 문서 필터링
    filtered_documents = [doc for doc in documents if doc]
    total_chunks = len(filtered_documents)

    if total_chunks == 0:
        return {
            "total_chunks": 0,
            "avg_chunk_length": 0.0,
        }

    # 평균 청크 길이 계산 (문자 수 기준)
    total_length = sum(len(doc) for doc in filtered_documents)
    avg_length = total_length / total_chunks

    return {
        "total_chunks": total_chunks,
        "avg_chunk_length": round(avg_length, 1),
    }
