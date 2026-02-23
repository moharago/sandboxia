"""R3 법령 RAG 평가 공통 모듈

run_evaluation.py와 run_llm_evaluation.py에서 공유하는 함수들.

주요 기능:
- 평가셋 로드
- Vector Store 연결
- Gold chunk ID 생성 및 매칭 (청킹 전략별 동적 매칭 지원)
- Retrieval 지표 계산

매칭 전략:
- article: law_name + article_no + article_title 매칭
- paragraph: 위 + paragraph_no 매칭
"""

import json
from enum import Enum
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from app.db.vector import create_embeddings
from app.rag.config import EmbeddingConfig
from eval.metrics import RetrievalMetrics


class ChunkLevel(str, Enum):
    """청킹 단위 (매칭 전략)"""

    ARTICLE = "article"  # 조 단위 매칭
    PARAGRAPH = "paragraph"  # 항 단위 매칭


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
    chunk_level: ChunkLevel = ChunkLevel.ARTICLE,
) -> tuple[list[dict], list[dict]]:
    """gold_citations에서 매칭용 ID 생성

    매칭 키 (chunk_level에 따라 다름):
    - article: law_name + article_no + article_title
    - paragraph: 위 + paragraph_no (여러 항이면 각각 별도 ID)

    Args:
        gold_citations: 평가셋의 gold_citations 목록
        chunk_level: 청킹 단위 (article 또는 paragraph)

    Returns:
        (all_gold_ids, must_have_ids)
    """
    all_ids = []
    must_have_ids = []

    for citation in gold_citations:
        law_name = citation.get("law_name", "")
        article_no = citation.get("article_no", "")
        article_title = citation.get("article_title", "")
        paragraph_nos = citation.get("paragraph_no")  # None, 단일값, 또는 리스트
        must_have = citation.get("must_have", False)

        # 기본 매칭 키: law_name + article_no
        base_id = f"{law_name}|{article_no}"

        if chunk_level == ChunkLevel.PARAGRAPH and paragraph_nos:
            # 항 단위 매칭: 각 paragraph_no에 대해 별도 ID 생성
            if isinstance(paragraph_nos, list):
                para_list = paragraph_nos
            else:
                para_list = [paragraph_nos]

            for para in para_list:
                gold_id = {
                    "base_id": base_id,
                    "article_title": article_title,
                    "paragraph_no": para,
                }
                all_ids.append(gold_id)
                if must_have:
                    must_have_ids.append(gold_id)
        else:
            # 조 단위 매칭: paragraph_no 무시
            gold_id = {
                "base_id": base_id,
                "article_title": article_title,
                "paragraph_no": None,
            }
            all_ids.append(gold_id)
            if must_have:
                must_have_ids.append(gold_id)

    return all_ids, must_have_ids


def extract_chunk_id_from_doc(doc) -> dict:
    """Document에서 매칭용 chunk_id 추출

    Returns:
        {
            "base_id": "법령명|조번호",
            "article_title": "조 제목",
            "paragraph_no": "항번호" (있으면)
        }
    """
    meta = doc.metadata
    base_id = f"{meta.get('law_name', '')}|{meta.get('article_no', '')}"
    article_title = meta.get("article_title", "")
    paragraph_no = meta.get("paragraph_no", "")

    return {
        "base_id": base_id,
        "article_title": article_title,
        "paragraph_no": paragraph_no if paragraph_no else None,
    }


def match_ids(
    retrieved_id: dict,
    gold_id: dict,
    chunk_level: ChunkLevel = ChunkLevel.ARTICLE,
) -> bool:
    """두 ID가 매칭되는지 확인

    매칭 규칙 (chunk_level에 따라 다름):
    - article: base_id + article_title 매칭
    - paragraph: 위 + paragraph_no 매칭

    Args:
        retrieved_id: 검색된 청크의 ID
        gold_id: 정답 청크의 ID
        chunk_level: 청킹 단위

    Returns:
        매칭 여부
    """
    # 1. base_id (law_name + article_no) 필수 일치
    if retrieved_id["base_id"] != gold_id["base_id"]:
        return False

    # 2. gold에 article_title이 있으면 검증
    if gold_id.get("article_title"):
        if retrieved_id.get("article_title") != gold_id["article_title"]:
            return False

    # 3. paragraph 레벨이고 gold에 paragraph_no가 있으면 검증
    if chunk_level == ChunkLevel.PARAGRAPH and gold_id.get("paragraph_no"):
        if retrieved_id.get("paragraph_no") != gold_id["paragraph_no"]:
            return False

    return True


def calculate_retrieval_metrics(
    retrieved_ids: list[dict],
    gold_ids: list[dict],
    must_have_ids: list[dict],
    k: int,
    chunk_level: ChunkLevel = ChunkLevel.ARTICLE,
) -> RetrievalMetrics:
    """매칭 로직을 적용한 Retrieval 지표 계산

    Args:
        retrieved_ids: 검색된 청크 ID 목록
        gold_ids: 전체 정답 청크 ID 목록
        must_have_ids: 핵심 정답 청크 ID 목록
        k: Top-K 값
        chunk_level: 청킹 단위 (매칭 기준)

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
                if match_ids(ret, gold, chunk_level):
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
                if match_ids(ret, gold, chunk_level):
                    matched_must_have += 1
                    break
        must_have_recall = matched_must_have / len(must_have_ids)
        retrieved_must_have = matched_must_have

    # MRR: 첫 번째 정답의 역순위
    mrr = 0.0
    first_hit_rank = None
    for rank, ret in enumerate(retrieved_ids, start=1):
        for gold in gold_ids:
            if match_ids(ret, gold, chunk_level):
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
    result = chunk_id["base_id"]

    if chunk_id.get("article_title"):
        result += f"|{chunk_id['article_title']}"

    if chunk_id.get("paragraph_no"):
        result += f" {chunk_id['paragraph_no']}"

    return result


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
