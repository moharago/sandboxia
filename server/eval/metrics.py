"""RAG 평가 공통 지표 계산 모듈

Retrieval 품질 평가를 위한 표준 지표들을 제공합니다.

지표:
- Recall@K: Top-K 안에 gold 청크 포함 비율
- Must-Have Recall@K: must_have=true인 핵심 청크 검색률
- MRR (Mean Reciprocal Rank): 첫 번째 정답의 역순위 평균
"""

from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    """Retrieval 평가 지표 결과"""

    recall_at_k: float
    must_have_recall_at_k: float
    mrr: float
    k: int

    # 세부 정보
    total_gold: int
    retrieved_gold: int
    total_must_have: int
    retrieved_must_have: int
    first_hit_rank: int | None  # 첫 번째 정답 순위 (없으면 None)


def calculate_recall_at_k(
    retrieved_ids: list[str],
    gold_ids: list[str],
    k: int,
) -> tuple[float, int, int]:
    """Recall@K 계산

    Args:
        retrieved_ids: 검색된 청크 ID 목록 (순서대로)
        gold_ids: 정답 청크 ID 목록
        k: Top-K

    Returns:
        (recall, retrieved_count, total_count)
    """
    if not gold_ids:
        return 1.0, 0, 0

    top_k_ids = set(retrieved_ids[:k])
    gold_set = set(gold_ids)

    retrieved_count = len(top_k_ids & gold_set)
    total_count = len(gold_set)

    recall = retrieved_count / total_count
    return recall, retrieved_count, total_count


def calculate_mrr(
    retrieved_ids: list[str],
    gold_ids: list[str],
) -> tuple[float, int | None]:
    """MRR (Mean Reciprocal Rank) 계산

    첫 번째 정답이 나타나는 순위의 역수를 반환합니다.

    Args:
        retrieved_ids: 검색된 청크 ID 목록 (순서대로)
        gold_ids: 정답 청크 ID 목록

    Returns:
        (mrr, first_hit_rank): MRR 값과 첫 번째 정답 순위
    """
    if not gold_ids:
        return 1.0, None

    gold_set = set(gold_ids)

    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in gold_set:
            return 1.0 / rank, rank

    return 0.0, None


def calculate_retrieval_metrics(
    retrieved_ids: list[str],
    gold_ids: list[str],
    must_have_ids: list[str],
    k: int = 5,
) -> RetrievalMetrics:
    """Retrieval 평가 지표 일괄 계산

    Args:
        retrieved_ids: 검색된 청크 ID 목록 (순서대로)
        gold_ids: 전체 정답 청크 ID 목록
        must_have_ids: 핵심 정답(must_have=true) 청크 ID 목록
        k: Top-K 값

    Returns:
        RetrievalMetrics 객체
    """
    # Recall@K
    recall, retrieved_gold, total_gold = calculate_recall_at_k(
        retrieved_ids, gold_ids, k
    )

    # Must-Have Recall@K
    must_have_recall, retrieved_must_have, total_must_have = calculate_recall_at_k(
        retrieved_ids, must_have_ids, k
    )

    # MRR
    mrr, first_hit_rank = calculate_mrr(retrieved_ids, gold_ids)

    return RetrievalMetrics(
        recall_at_k=recall,
        must_have_recall_at_k=must_have_recall,
        mrr=mrr,
        k=k,
        total_gold=total_gold,
        retrieved_gold=retrieved_gold,
        total_must_have=total_must_have,
        retrieved_must_have=retrieved_must_have,
        first_hit_rank=first_hit_rank,
    )


def aggregate_metrics(metrics_list: list[RetrievalMetrics]) -> dict:
    """여러 평가 항목의 지표를 집계

    Args:
        metrics_list: 각 평가 항목별 RetrievalMetrics 목록

    Returns:
        집계된 평균 지표
    """
    if not metrics_list:
        return {}

    n = len(metrics_list)
    k = metrics_list[0].k

    avg_recall = sum(m.recall_at_k for m in metrics_list) / n
    avg_must_have_recall = sum(m.must_have_recall_at_k for m in metrics_list) / n
    avg_mrr = sum(m.mrr for m in metrics_list) / n

    # 전체 청크 기준 통계
    total_gold = sum(m.total_gold for m in metrics_list)
    total_retrieved = sum(m.retrieved_gold for m in metrics_list)
    total_must_have = sum(m.total_must_have for m in metrics_list)
    total_must_have_retrieved = sum(m.retrieved_must_have for m in metrics_list)

    return {
        "k": k,
        "num_queries": n,
        "avg_recall_at_k": round(avg_recall, 4),
        "avg_must_have_recall_at_k": round(avg_must_have_recall, 4),
        "avg_mrr": round(avg_mrr, 4),
        "total_gold_citations": total_gold,
        "total_retrieved_gold": total_retrieved,
        "total_must_have_citations": total_must_have,
        "total_must_have_retrieved": total_must_have_retrieved,
    }
