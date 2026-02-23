"""R3 법령 RAG 평가 스크립트

평가 지표:
- Must-Have Recall@K: 핵심 조항(must_have=true) 검색률
- Recall@K: 전체 gold_citations 검색률
- MRR: 첫 번째 정답 조항의 역순위
- Latency (P50): 검색 응답 시간

실행:
    cd server
    uv run python eval/r3/run_evaluation.py

옵션:
    --top_k 10              # Top-K 값 변경 (기본: 5)
    --output result         # 결과 파일명 (기본: 타임스탬프)
    --config E2             # 임베딩 설정 (없으면 .env 사용)
    --collection_suffix _E2 # 컬렉션 접미사
    --chunk_level paragraph # 매칭 단위: article(조) 또는 paragraph(항)

매칭 단위 설명:
- article: 조 단위 매칭 (법명 + 조번호 + 조제목)
  → 조 단위 청킹(C5, C6)에 적합
- paragraph: 항 단위 매칭 (법명 + 조번호 + 조제목 + 항번호)
  → 항 단위 청킹(C0~C4)에 적합
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
from app.core.constants import COLLECTION_LAWS
from app.rag.config import EmbeddingConfig, load_embedding_config
from eval.metrics import RetrievalMetrics, aggregate_metrics
from eval.r3.common import (
    RESULTS_DIR_RETRIEVAL,
    ChunkLevel,
    build_gold_chunk_ids,
    calculate_retrieval_metrics,
    extract_chunk_id_from_doc,
    format_chunk_ids,
    get_chunk_statistics,
    get_vector_store,
    load_evaluation_set,
)


def evaluate_single_item(
    vector_store,
    item: dict,
    top_k: int = 5,
    chunk_level: ChunkLevel = ChunkLevel.ARTICLE,
) -> tuple[RetrievalMetrics, float, dict]:
    """단일 평가 항목 평가

    Args:
        vector_store: Vector Store
        item: 평가 항목
        top_k: Top-K 값
        chunk_level: 청킹 단위 (매칭 기준)

    Returns:
        (metrics, latency_ms, detail_info)
    """
    question = item["question"]
    gold_citations = item.get("gold_citations", [])

    # gold ID 생성 (chunk_level에 따라 다르게 생성)
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_citations, chunk_level)

    # 검색 실행 (시간 측정)
    start_time = time.perf_counter()
    results = vector_store.similarity_search(question, k=top_k)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # 검색 결과에서 chunk_id 추출
    retrieved_ids = [extract_chunk_id_from_doc(doc) for doc in results]

    # 지표 계산 (커스텀 매칭 로직 적용)
    metrics = calculate_retrieval_metrics(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        k=top_k,
        chunk_level=chunk_level,
    )

    # 상세 정보 (읽기 쉬운 형식으로 변환)
    detail = {
        "id": item["id"],
        "domain": item.get("domain", ""),
        "question": question,
        "gold_ids": format_chunk_ids(gold_ids),
        "must_have_ids": format_chunk_ids(must_have_ids),
        "retrieved_ids": format_chunk_ids(retrieved_ids[:top_k]),
        "recall_at_k": metrics.recall_at_k,
        "must_have_recall_at_k": metrics.must_have_recall_at_k,
        "mrr": metrics.mrr,
        "first_hit_rank": metrics.first_hit_rank,
        "latency_ms": round(latency_ms, 2),
    }

    return metrics, latency_ms, detail


def run_evaluation(
    top_k: int = 5,
    output_name: str | None = None,
    embedding_config: EmbeddingConfig | None = None,
    collection_suffix: str = "",
    chunk_level: ChunkLevel = ChunkLevel.ARTICLE,
    vectordb_type: str = "chroma",
):
    """전체 평가 실행

    Args:
        top_k: Top-K 값
        output_name: 결과 파일명 (없으면 타임스탬프 사용)
        embedding_config: 임베딩 설정 (None이면 .env의 LLM_EMBEDDING_MODEL 사용)
        collection_suffix: 컬렉션 이름에 붙일 접미사
        chunk_level: 청킹 단위 (매칭 기준) - article 또는 paragraph
        vectordb_type: 사용할 Vector DB (chroma 또는 qdrant)
    """
    print("=" * 60)
    print("R3 법령 RAG 평가 시작")
    print("=" * 60)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("evaluation_items", [])
    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    print(f"매칭 단위: {chunk_level.value}")
    if embedding_config:
        print(f"임베딩: {embedding_config.name} ({embedding_config.model})")
    else:
        print(f"임베딩: .env 기본값 ({settings.LLM_EMBEDDING_MODEL})")
    print(f"컬렉션: {COLLECTION_LAWS}{collection_suffix}")
    print(f"Vector DB: {vectordb_type.upper()}")

    # Vector Store 초기화
    print("\nVector Store 초기화 중...")
    vector_store = get_vector_store(embedding_config, collection_suffix, vectordb_type)

    # 평가 실행
    print("\n평가 진행 중...\n")
    all_metrics: list[RetrievalMetrics] = []
    all_latencies: list[float] = []
    all_details: list[dict] = []

    for i, item in enumerate(items, 1):
        metrics, latency, detail = evaluate_single_item(vector_store, item, top_k, chunk_level)
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
        sorted(all_latencies)[int(len(all_latencies) * 0.95)] if len(all_latencies) >= 20 else max(all_latencies)
    )
    latency_mean = statistics.mean(all_latencies)

    # 결과 출력
    print("\n" + "=" * 60)
    print("평가 결과 요약")
    print("=" * 60)
    print(f"\n📊 Retrieval 지표 (K={top_k}):")
    print(f"  - Must-Have Recall@{top_k}: {aggregated['avg_must_have_recall_at_k']:.4f}")
    print(f"  - Recall@{top_k}:           {aggregated['avg_recall_at_k']:.4f}")
    print(f"  - MRR:                      {aggregated['avg_mrr']:.4f}")

    print("\n⏱️  Latency:")
    print(f"  - P50: {latency_p50:.1f}ms")
    print(f"  - P95: {latency_p95:.1f}ms")
    print(f"  - Mean: {latency_mean:.1f}ms")

    print("\n📈 세부 통계:")
    print(f"  - 총 gold_citations: {aggregated['total_gold_citations']}")
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

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "top_k": top_k,
            "chunk_level": chunk_level.value,
            "embedding_config": embedding_config.name if embedding_config else ".env",
            "embedding_model": embedding_config.model if embedding_config else settings.LLM_EMBEDDING_MODEL,
            "embedding_provider": embedding_config.provider if embedding_config else "openai",
            "collection": COLLECTION_LAWS + collection_suffix,
            "vectordb": vectordb_type,
            "num_items": len(items),
        },
        "summary": {
            "must_have_recall_at_k": aggregated["avg_must_have_recall_at_k"],
            "recall_at_k": aggregated["avg_recall_at_k"],
            "mrr": aggregated["avg_mrr"],
            "latency_p50_ms": round(latency_p50, 2),
            "latency_p95_ms": round(latency_p95, 2),
            "latency_mean_ms": round(latency_mean, 2),
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

    parser = argparse.ArgumentParser(description="R3 법령 RAG 평가")
    parser.add_argument("--top_k", type=int, default=5, help="Top-K 값 (기본: 5)")
    parser.add_argument("--output", type=str, default=None, help="결과 파일명")
    parser.add_argument("--config", type=str, default=None, help="임베딩 설정 (없으면 .env 사용)")
    parser.add_argument("--collection_suffix", type=str, default="", help="컬렉션 접미사")
    parser.add_argument(
        "--chunk_level",
        type=str,
        default="article",
        choices=["article", "paragraph"],
        help="매칭 단위: article(조 단위) 또는 paragraph(항 단위) (기본: article)",
    )
    parser.add_argument(
        "--vectordb",
        type=str,
        default="chroma",
        choices=["chroma", "qdrant"],
        help="사용할 Vector DB (기본: chroma)",
    )

    args = parser.parse_args()

    # 임베딩 설정 로드 (프리셋 지정 시에만)
    embedding_config = None
    if args.config:
        embedding_config = load_embedding_config(args.config)

    # 청킹 단위 파싱
    chunk_level = ChunkLevel(args.chunk_level)

    run_evaluation(
        top_k=args.top_k,
        output_name=args.output,
        embedding_config=embedding_config,
        collection_suffix=args.collection_suffix,
        chunk_level=chunk_level,
        vectordb_type=args.vectordb,
    )


if __name__ == "__main__":
    main()
