"""R2 승인 사례 RAG 평가 공통 모듈

run_evaluation.py에서 사용하는 공유 함수들.

주요 기능:
- 평가셋/원본 데이터 로드
- 전략별 임시 Vector Store 생성
- Gold case ID 매칭
- Retrieval 지표 계산
"""

import json
import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from eval.metrics import RetrievalMetrics

# 경로 설정
EVAL_DIR = Path(__file__).parent
EVALUATION_SET_PATH = EVAL_DIR / "evaluation_set.json"
RESULTS_DIR = EVAL_DIR / "results" / "retrieval"
DATA_DIR = EVAL_DIR.parent.parent / "data" / "r2_data"
DATA_PATH = DATA_DIR / "cases_structured.json"
DATA_PATH_ENRICHED = DATA_DIR / "cases_structured_enriched.json"

VALID_STRATEGIES = ("structured", "hybrid", "fulltext")
VALID_DATA_VERSIONS = ("original", "enriched")


def load_evaluation_set() -> dict:
    """평가셋 로드"""
    with open(EVALUATION_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_case_data(data_version: str = "original") -> list[dict]:
    """케이스 데이터 로드

    Args:
        data_version: "original" (원본) 또는 "enriched" (보강본)
    """
    path = DATA_PATH_ENRICHED if data_version == "enriched" else DATA_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_temp_vector_store(
    data: list[dict],
    strategy: str,
    collection_name: str = "r2_eval_temp",
) -> tuple[Chroma, chromadb.ClientAPI]:
    """전략별 임시 Vector Store 생성 (EphemeralClient)

    Args:
        data: 원본 케이스 데이터
        strategy: 데이터 전략 (structured / hybrid / fulltext)
        collection_name: 임시 컬렉션명

    Returns:
        (vectorstore, chroma_client) - 평가 후 client로 컬렉션 삭제 가능
    """
    from scripts.collect_cases import create_documents

    # Document 생성 (collect_cases.py의 로직 재사용)
    documents, doc_ids = create_documents(data, strategy=strategy)

    # EphemeralClient로 임시 컬렉션 생성
    client = chromadb.EphemeralClient()
    embeddings = OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )

    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    # 문서 추가
    vectorstore.add_documents(documents, ids=doc_ids)

    return vectorstore, client


def build_gold_case_ids(
    gold_cases: list[dict],
) -> tuple[list[str], list[str]]:
    """gold_cases에서 case_id 추출

    Returns:
        (all_ids, must_have_ids)
    """
    all_ids = [g["case_id"] for g in gold_cases]
    must_have_ids = [g["case_id"] for g in gold_cases if g.get("must_have")]
    return all_ids, must_have_ids


def extract_case_id_from_result(doc) -> str:
    """검색 결과 Document에서 case_id 추출"""
    return doc.metadata.get("case_id", "")


def calculate_r2_metrics(
    retrieved_ids: list[str],
    gold_ids: list[str],
    must_have_ids: list[str],
    negative_ids: list[str],
    k: int,
) -> tuple[RetrievalMetrics, float]:
    """R2용 Retrieval 지표 계산

    공통 metrics.py의 RetrievalMetrics + Negative@K 추가.

    Args:
        retrieved_ids: 검색된 case_id 목록
        gold_ids: 전체 정답 case_id 목록
        must_have_ids: 핵심 정답 case_id 목록
        negative_ids: 검색되면 안 되는 case_id 목록
        k: Top-K 값

    Returns:
        (metrics, negative_at_k)
    """
    top_k = retrieved_ids[:k]
    top_k_set = set(top_k)

    # Recall@K
    if not gold_ids:
        recall = 1.0
        retrieved_gold = 0
    else:
        gold_set = set(gold_ids)
        retrieved_gold = len(top_k_set & gold_set)
        recall = retrieved_gold / len(gold_set)

    # Must-Have Recall@K
    if not must_have_ids:
        must_have_recall = 1.0
        retrieved_must_have = 0
    else:
        mh_set = set(must_have_ids)
        retrieved_must_have = len(top_k_set & mh_set)
        must_have_recall = retrieved_must_have / len(mh_set)

    # MRR (top_k 범위 내에서만 계산)
    mrr = 0.0
    first_hit_rank = None
    gold_set = set(gold_ids)
    for rank, rid in enumerate(top_k, start=1):
        if rid in gold_set:
            mrr = 1.0 / rank
            first_hit_rank = rank
            break

    metrics = RetrievalMetrics(
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

    # Negative@K: 검색되면 안 되는 사례 포함 비율
    if not negative_ids:
        negative_at_k = 0.0
    else:
        neg_set = set(negative_ids)
        neg_count = len(top_k_set & neg_set)
        negative_at_k = neg_count / len(neg_set)

    return metrics, negative_at_k
