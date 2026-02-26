"""R1 규제제도 & 절차 RAG 평가 스크립트

평가 지표:
- Must-Have Recall@5: 핵심 청크(must_have=true) 검색률
- Recall@5: 전체 gold_chunks 검색률
- MRR: 첫 번째 정답 청크의 역순위
- Latency (P50): 검색 응답 시간

실행:
    cd server
    uv run python eval/r1/run_evaluation.py

옵션:
    --top_k 10        # Top-K 값 변경 (기본: 5)
    --output result   # 결과 파일명 (기본: 타임스탬프)
    --config E2       # 임베딩 설정 (없으면 .env 사용)
    --collection_suffix _E2  # 컬렉션 접미사
    --hybrid          # Hybrid Search (BM25 + Vector)
    --vector_weight 0.5  # Hybrid에서 벡터 가중치 (기본: 0.5)
    --rerank          # Re-ranking (Bi-encoder + Cross-encoder)
    --rerank_candidates 20  # Re-ranking 초기 후보 수 (기본: 20)
"""

import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from app.core.constants import COLLECTION_REGULATIONS
from app.rag.config import EmbeddingConfig, load_embedding_config
from eval.metrics import RetrievalMetrics, aggregate_metrics
from eval.r1.common import (
    RESULTS_DIR_RETRIEVAL,
    build_gold_chunk_ids,
    calculate_retrieval_metrics,
    extract_chunk_id_from_doc,
    get_chunk_statistics,
    get_hybrid_retriever,
    get_reranker_retriever,
    get_vector_store,
    load_evaluation_set,
)


def evaluate_single_item_vector(
    vector_store,
    item: dict,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, float, dict]:
    """단일 평가 항목 평가 (Vector Search)"""
    question = item["question"]
    gold_chunks = item.get("gold_chunks", [])
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_chunks)

    # 검색 실행 (시간 측정)
    start_time = time.perf_counter()
    results = vector_store.similarity_search(question, k=top_k)
    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    # 검색 결과에서 chunk_id 추출
    retrieved_ids = [extract_chunk_id_from_doc(doc) for doc in results]

    # 지표 계산
    metrics = calculate_retrieval_metrics(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        k=top_k,
    )

    detail = {
        "id": item["id"],
        "category": item.get("category", ""),
        "track": item.get("track", ""),
        "question": question,
        "gold_ids": gold_ids,
        "must_have_ids": must_have_ids,
        "retrieved_ids": retrieved_ids[:top_k],
        "recall_at_k": metrics.recall_at_k,
        "must_have_recall_at_k": metrics.must_have_recall_at_k,
        "mrr": metrics.mrr,
        "first_hit_rank": metrics.first_hit_rank,
        "latency_ms": round(latency_ms, 2),
    }

    return metrics, latency_ms, detail


def evaluate_single_item_hybrid(
    retriever,
    item: dict,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, float, dict]:
    """단일 평가 항목 평가 (Hybrid Search)"""
    question = item["question"]
    gold_chunks = item.get("gold_chunks", [])
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_chunks)

    # 검색 실행 (시간 측정)
    start_time = time.perf_counter()
    results = retriever.invoke(question)[:top_k]
    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    # 검색 결과에서 chunk_id 추출
    retrieved_ids = [extract_chunk_id_from_doc(doc) for doc in results]

    # 지표 계산
    metrics = calculate_retrieval_metrics(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        k=top_k,
    )

    detail = {
        "id": item["id"],
        "category": item.get("category", ""),
        "track": item.get("track", ""),
        "question": question,
        "gold_ids": gold_ids,
        "must_have_ids": must_have_ids,
        "retrieved_ids": retrieved_ids[:top_k],
        "recall_at_k": metrics.recall_at_k,
        "must_have_recall_at_k": metrics.must_have_recall_at_k,
        "mrr": metrics.mrr,
        "first_hit_rank": metrics.first_hit_rank,
        "latency_ms": round(latency_ms, 2),
    }

    return metrics, latency_ms, detail


def evaluate_single_item_rerank(
    retriever,
    item: dict,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, float, float, dict]:
    """단일 평가 항목 평가 (Re-ranking: Bi-encoder + Cross-encoder)

    Returns:
        (metrics, retrieval_latency_ms, rerank_latency_ms, detail)
    """
    question = item["question"]
    gold_chunks = item.get("gold_chunks", [])
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_chunks)

    # Re-ranking 검색 실행
    results, retrieval_latency_ms, rerank_latency_ms = retriever.invoke(question)
    total_latency_ms = retrieval_latency_ms + rerank_latency_ms

    # 검색 결과에서 chunk_id 추출
    retrieved_ids = [extract_chunk_id_from_doc(doc) for doc in results]

    # 지표 계산
    metrics = calculate_retrieval_metrics(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        k=top_k,
    )

    detail = {
        "id": item["id"],
        "category": item.get("category", ""),
        "track": item.get("track", ""),
        "question": question,
        "gold_ids": gold_ids,
        "must_have_ids": must_have_ids,
        "retrieved_ids": retrieved_ids[:top_k],
        "recall_at_k": metrics.recall_at_k,
        "must_have_recall_at_k": metrics.must_have_recall_at_k,
        "mrr": metrics.mrr,
        "first_hit_rank": metrics.first_hit_rank,
        "retrieval_latency_ms": round(retrieval_latency_ms, 2),
        "rerank_latency_ms": round(rerank_latency_ms, 2),
        "total_latency_ms": round(total_latency_ms, 2),
    }

    return metrics, total_latency_ms, rerank_latency_ms, detail


def run_evaluation(
    top_k: int = 5,
    output_name: str | None = None,
    embedding_config: EmbeddingConfig | None = None,
    collection_suffix: str = "",
    hybrid: bool = False,
    vector_weight: float = 0.5,
    rerank: bool = False,
    rerank_candidates: int = 20,
):
    """전체 평가 실행

    Args:
        top_k: Top-K 값
        output_name: 결과 파일명 (없으면 타임스탬프 사용)
        embedding_config: 임베딩 설정 (None이면 .env의 LLM_EMBEDDING_MODEL 사용)
        collection_suffix: 컬렉션 이름에 붙일 접미사
        hybrid: Hybrid Search 사용 여부
        vector_weight: Hybrid에서 벡터 가중치 (0.0~1.0)
        rerank: Re-ranking 사용 여부
        rerank_candidates: Re-ranking 초기 후보 수 (기본: 20)
    """
    print("=" * 60)
    print("R1 규제제도 & 절차 RAG 평가 시작")
    print("=" * 60)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("questions", [])
    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    if embedding_config:
        print(f"임베딩: {embedding_config.name} ({embedding_config.model})")
    else:
        print(f"임베딩: .env 기본값 ({settings.LLM_EMBEDDING_MODEL})")
    print(f"컬렉션: {COLLECTION_REGULATIONS}{collection_suffix}")

    if rerank:
        print(f"검색 방식: Re-ranking (Bi-encoder Top-{rerank_candidates} → Cross-encoder Top-{top_k})")
    elif hybrid:
        print(f"검색 방식: Hybrid (BM25 + Vector, weight={vector_weight})")
    else:
        print("검색 방식: Vector Only")

    # Retriever 초기화
    if rerank:
        print("\nRe-ranking Retriever 초기화 중...")
        print("  - Bi-encoder: Vector Store (빠른 후보 검색)")
        print("  - Cross-encoder: BGE Reranker (정밀 재정렬)")
        retriever = get_reranker_retriever(
            embedding_config, collection_suffix, rerank_candidates, top_k
        )
        vector_store = get_vector_store(embedding_config, collection_suffix)
    elif hybrid:
        print("\nHybrid Retriever 초기화 중...")
        retriever = get_hybrid_retriever(
            embedding_config, collection_suffix, vector_weight, top_k
        )
        vector_store = get_vector_store(embedding_config, collection_suffix)
    else:
        print("\nVector Store 초기화 중...")
        vector_store = get_vector_store(embedding_config, collection_suffix)

    # 평가 실행
    print("\n평가 진행 중...\n")
    all_metrics: list[RetrievalMetrics] = []
    all_latencies: list[float] = []
    all_rerank_latencies: list[float] = []  # Re-ranking latency 별도 추적
    all_details: list[dict] = []

    for i, item in enumerate(items, 1):
        if rerank:
            metrics, latency, rerank_latency, detail = evaluate_single_item_rerank(
                retriever, item, top_k
            )
            all_rerank_latencies.append(rerank_latency)
        elif hybrid:
            metrics, latency, detail = evaluate_single_item_hybrid(
                retriever, item, top_k
            )
        else:
            metrics, latency, detail = evaluate_single_item_vector(
                vector_store, item, top_k
            )

        all_metrics.append(metrics)
        all_latencies.append(latency)
        all_details.append(detail)

        # 진행 상황 출력
        status = "✓" if metrics.must_have_recall_at_k == 1.0 else "✗"
        print(
            f"  [{i:2d}/{len(items)}] {status} {item['id']} | "
            f"MH-Recall: {metrics.must_have_recall_at_k:.2f} | "
            f"Recall: {metrics.recall_at_k:.2f} | "
            f"MRR: {metrics.mrr:.2f} | "
            f"Latency: {latency:.0f}ms"
        )

    # 집계
    aggregated = aggregate_metrics(all_metrics)

    # 청크 통계 추가
    chunk_stats = get_chunk_statistics(vector_store)
    aggregated["total_chunks"] = chunk_stats["total_chunks"]
    aggregated["avg_chunk_length"] = chunk_stats["avg_chunk_length"]

    # Latency 통계
    latency_p50 = statistics.median(all_latencies)
    latency_p95 = (
        sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        if len(all_latencies) >= 20
        else max(all_latencies)
    )
    latency_mean = statistics.mean(all_latencies)

    # Re-ranking latency 통계 (rerank 모드일 때만)
    rerank_latency_mean = None
    if rerank and all_rerank_latencies:
        rerank_latency_mean = statistics.mean(all_rerank_latencies)

    # 결과 출력
    print("\n" + "=" * 60)
    print("평가 결과 요약")
    print("=" * 60)
    print(f"\n📊 Retrieval 지표 (K={top_k}):")
    print(f"  - Must-Have Recall@{top_k}: {aggregated['avg_must_have_recall_at_k']:.4f}")
    print(f"  - Recall@{top_k}:           {aggregated['avg_recall_at_k']:.4f}")
    print(f"  - MRR:                      {aggregated['avg_mrr']:.4f}")

    print("\n⏱️  Latency (Total):")
    print(f"  - P50: {latency_p50:.1f}ms")
    print(f"  - P95: {latency_p95:.1f}ms")
    print(f"  - Mean: {latency_mean:.1f}ms")

    if rerank and rerank_latency_mean:
        print(f"\n🔄 Re-ranking Latency:")
        print(f"  - Mean: {rerank_latency_mean:.1f}ms")

    print("\n📈 세부 통계:")
    print(f"  - 총 gold_chunks: {aggregated['total_gold_citations']}")
    print(f"  - 검색된 gold: {aggregated['total_retrieved_gold']}")
    print(f"  - 총 must_have: {aggregated['total_must_have_citations']}")
    print(f"  - 검색된 must_have: {aggregated['total_must_have_retrieved']}")

    print("\n📦 청크 통계:")
    print(f"  - 총 청크 수: {aggregated['total_chunks']:,}")
    print(f"  - 평균 청크 길이: {aggregated['avg_chunk_length']:.1f}자")

    # 결과 저장
    RESULTS_DIR_RETRIEVAL.mkdir(parents=True, exist_ok=True)

    if output_name:
        result_filename = f"{output_name}.json"
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        result_filename = f"{timestamp}.json"

    result_path = RESULTS_DIR_RETRIEVAL / result_filename

    # 검색 타입 결정
    if rerank:
        search_type = "rerank"
    elif hybrid:
        search_type = "hybrid"
    else:
        search_type = "vector"

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "top_k": top_k,
            "embedding_config": embedding_config.name if embedding_config else ".env",
            "embedding_model": (
                embedding_config.model if embedding_config else settings.LLM_EMBEDDING_MODEL
            ),
            "embedding_provider": (
                embedding_config.provider if embedding_config else "openai"
            ),
            "collection": COLLECTION_REGULATIONS + collection_suffix,
            "num_items": len(items),
            "search_type": search_type,
            "vector_weight": vector_weight if hybrid else None,
            "rerank_candidates": rerank_candidates if rerank else None,
            "rerank_model": "BAAI/bge-reranker-v2-m3" if rerank else None,
        },
        "summary": {
            "must_have_recall_at_k": aggregated["avg_must_have_recall_at_k"],
            "recall_at_k": aggregated["avg_recall_at_k"],
            "mrr": aggregated["avg_mrr"],
            "latency_p50_ms": round(latency_p50, 2),
            "latency_p95_ms": round(latency_p95, 2),
            "latency_mean_ms": round(latency_mean, 2),
            "rerank_latency_mean_ms": round(rerank_latency_mean, 2) if rerank_latency_mean else None,
        },
        "aggregated": aggregated,
        "details": all_details,
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 결과 저장: {result_path}")


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="R1 규제제도 & 절차 RAG 평가")
    parser.add_argument("--top_k", type=int, default=5, help="Top-K 값 (기본: 5)")
    parser.add_argument("--output", type=str, default=None, help="결과 파일명")
    parser.add_argument(
        "--config", type=str, default=None, help="임베딩 설정 (없으면 .env 사용)"
    )
    parser.add_argument(
        "--collection_suffix", type=str, default="", help="컬렉션 접미사"
    )
    parser.add_argument(
        "--hybrid", action="store_true", help="Hybrid Search (BM25 + Vector) 사용"
    )
    parser.add_argument(
        "--vector_weight",
        type=float,
        default=0.5,
        help="Hybrid에서 벡터 가중치 (기본: 0.5)",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="Re-ranking (Bi-encoder + Cross-encoder) 사용",
    )
    parser.add_argument(
        "--rerank_candidates",
        type=int,
        default=20,
        help="Re-ranking 초기 후보 수 (기본: 20)",
    )

    args = parser.parse_args()

    # 임베딩 설정 로드 (프리셋 지정 시에만)
    embedding_config = None
    if args.config:
        embedding_config = load_embedding_config(args.config, rag_type="r1")

    run_evaluation(
        top_k=args.top_k,
        output_name=args.output,
        embedding_config=embedding_config,
        collection_suffix=args.collection_suffix,
        hybrid=args.hybrid,
        vector_weight=args.vector_weight,
        rerank=args.rerank,
        rerank_candidates=args.rerank_candidates,
    )


if __name__ == "__main__":
    main()
