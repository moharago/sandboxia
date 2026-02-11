"""R2 승인 사례 RAG 평가 스크립트

전략별 Retrieval 성능을 비교합니다.

평가 지표:
- Must-Have Recall@K: 핵심 사례(must_have=true) 검색률
- Recall@K: 전체 gold_cases 검색률
- MRR: 첫 번째 정답 사례의 역순위
- Negative@K: 검색되면 안 되는 사례 포함 비율 (낮을수록 좋음)
- Latency (P50): 검색 응답 시간

실행:
    cd server
    uv run python eval/r2/run_evaluation.py                    # structured만
    uv run python eval/r2/run_evaluation.py --strategy all     # 3개 전략 비교
    uv run python eval/r2/run_evaluation.py --strategy hybrid  # hybrid만

옵션:
    --strategy structured|hybrid|fulltext|all  (기본: structured)
    --top_k 10                                 (기본: 5)
    --output result                            (결과 파일명, 기본: 타임스탬프)
"""

import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from eval.metrics import RetrievalMetrics, aggregate_metrics
from eval.r2.common import (
    RESULTS_DIR,
    VALID_STRATEGIES,
    build_gold_case_ids,
    calculate_r2_metrics,
    create_temp_vector_store,
    extract_case_id_from_result,
    load_case_data,
    load_evaluation_set,
)


def evaluate_single_item(
    vectorstore,
    item: dict,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, float, float, dict]:
    """단일 평가 항목 평가

    Args:
        vectorstore: Chroma Vector Store
        item: 평가 항목
        top_k: Top-K 값

    Returns:
        (metrics, negative_at_k, latency_ms, detail_info)
    """
    question = item["question"]
    gold_cases = item.get("gold_cases", [])
    negatives = item.get("negatives", [])

    # gold / negative ID 생성
    gold_ids, must_have_ids = build_gold_case_ids(gold_cases)
    negative_ids = [n["case_id"] for n in negatives]

    # 검색 실행 (시간 측정)
    start_time = time.perf_counter()
    results = vectorstore.similarity_search(question, k=top_k)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # 검색 결과에서 case_id 추출
    retrieved_ids = [extract_case_id_from_result(doc) for doc in results]

    # 지표 계산
    metrics, negative_at_k = calculate_r2_metrics(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        negative_ids=negative_ids,
        k=top_k,
    )

    # 상세 정보
    detail = {
        "id": item["id"],
        "category": item.get("category", ""),
        "query_type": item.get("query_type", ""),
        "data_quality": item.get("data_quality", ""),
        "question": question,
        "gold_ids": gold_ids,
        "must_have_ids": must_have_ids,
        "negative_ids": negative_ids,
        "retrieved_ids": retrieved_ids[:top_k],
        "recall_at_k": metrics.recall_at_k,
        "must_have_recall_at_k": metrics.must_have_recall_at_k,
        "mrr": metrics.mrr,
        "negative_at_k": negative_at_k,
        "first_hit_rank": metrics.first_hit_rank,
        "latency_ms": round(latency_ms, 2),
    }

    return metrics, negative_at_k, latency_ms, detail


def run_single_strategy(
    strategy: str,
    case_data: list[dict],
    eval_items: list[dict],
    top_k: int = 5,
) -> dict:
    """단일 전략 평가 실행

    Args:
        strategy: 데이터 전략
        case_data: 원본 케이스 데이터
        eval_items: 평가 항목 리스트
        top_k: Top-K 값

    Returns:
        전략 평가 결과 dict
    """
    print(f"\n{'─' * 60}")
    print(f"전략: {strategy}")
    print(f"{'─' * 60}")

    # 임시 Vector Store 생성
    print(f"  Vector Store 생성 중 ({strategy})...")
    collection_name = f"r2_eval_{strategy}"

    build_start = time.perf_counter()
    vectorstore, client = create_temp_vector_store(
        case_data, strategy, collection_name
    )
    build_time = (time.perf_counter() - build_start) * 1000
    print(f"  Vector Store 준비 완료 ({build_time:.0f}ms)")

    # 평가 실행
    print("  평가 진행 중...\n")
    all_metrics: list[RetrievalMetrics] = []
    all_negatives: list[float] = []
    all_latencies: list[float] = []
    all_details: list[dict] = []

    for i, item in enumerate(eval_items, 1):
        metrics, neg_at_k, latency, detail = evaluate_single_item(
            vectorstore, item, top_k
        )
        all_metrics.append(metrics)
        all_negatives.append(neg_at_k)
        all_latencies.append(latency)
        all_details.append(detail)

        # 진행 상황 출력
        status = "O" if metrics.must_have_recall_at_k == 1.0 else "X"
        neg_mark = " [NEG!]" if neg_at_k > 0 else ""
        print(
            f"  [{i:2d}/{len(eval_items)}] {status} {item['id']} | "
            f"MH-R: {metrics.must_have_recall_at_k:.2f} | "
            f"R: {metrics.recall_at_k:.2f} | "
            f"MRR: {metrics.mrr:.2f} | "
            f"{latency:.0f}ms{neg_mark}"
        )

    # 집계
    aggregated = aggregate_metrics(all_metrics)

    # Latency 통계
    latency_p50 = statistics.median(all_latencies)
    latency_p95 = (
        sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        if len(all_latencies) >= 20
        else max(all_latencies)
    )
    latency_mean = statistics.mean(all_latencies)

    # Negative 통계
    avg_negative = statistics.mean(all_negatives) if all_negatives else 0.0
    items_with_neg = sum(1 for n in all_negatives if n > 0)

    # 결과 요약 출력
    print(f"\n  --- {strategy} 결과 ---")
    print(f"  Must-Have Recall@{top_k}: {aggregated['avg_must_have_recall_at_k']:.4f}")
    print(f"  Recall@{top_k}:           {aggregated['avg_recall_at_k']:.4f}")
    print(f"  MRR:                      {aggregated['avg_mrr']:.4f}")
    print(f"  Negative@{top_k}:          {avg_negative:.4f} ({items_with_neg}건 오염)")
    print(f"  Latency P50:              {latency_p50:.0f}ms")

    # 임시 컬렉션 삭제
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    return {
        "strategy": strategy,
        "summary": {
            "must_have_recall_at_k": aggregated["avg_must_have_recall_at_k"],
            "recall_at_k": aggregated["avg_recall_at_k"],
            "mrr": aggregated["avg_mrr"],
            "negative_at_k": round(avg_negative, 4),
            "items_with_negative": items_with_neg,
            "latency_p50_ms": round(latency_p50, 2),
            "latency_p95_ms": round(latency_p95, 2),
            "latency_mean_ms": round(latency_mean, 2),
        },
        "aggregated": aggregated,
        "details": all_details,
        "build_time_ms": round(build_time, 2),
    }


def print_comparison_table(results: list[dict], top_k: int):
    """전략 비교 테이블 출력"""
    print("\n" + "=" * 70)
    print("전략 비교 결과")
    print("=" * 70)

    # 헤더
    header = f"{'지표':<25}"
    for r in results:
        header += f"  {r['strategy']:>12}"
    print(header)
    print("─" * (25 + 14 * len(results)))

    # 지표 행
    metrics_rows = [
        ("Must-Have Recall@K", "must_have_recall_at_k"),
        ("Recall@K", "recall_at_k"),
        ("MRR", "mrr"),
        ("Negative@K (low=good)", "negative_at_k"),
        ("Latency P50 (ms)", "latency_p50_ms"),
    ]

    for label, key in metrics_rows:
        row = f"{label:<25}"
        values = [r["summary"][key] for r in results]
        best_idx = values.index(max(values))
        # Negative와 Latency는 낮을수록 좋음
        if key in ("negative_at_k", "latency_p50_ms"):
            best_idx = values.index(min(values))

        for i, r in enumerate(results):
            val = r["summary"][key]
            marker = " *" if i == best_idx else "  "
            if key == "latency_p50_ms":
                row += f"  {val:>9.0f}ms{marker}"
            else:
                row += f"  {val:>10.4f}{marker}"
        print(row)

    print("\n  * = 해당 지표 최고 성능")


def run_evaluation(
    strategy: str = "structured",
    top_k: int = 5,
    output_name: str | None = None,
):
    """전체 평가 실행

    Args:
        strategy: 데이터 전략 (structured / hybrid / fulltext / all)
        top_k: Top-K 값
        output_name: 결과 파일명 (없으면 타임스탬프 사용)
    """
    print("=" * 60)
    print("R2 승인 사례 RAG 평가 시작")
    print("=" * 60)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("evaluation_items", [])
    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    print(f"임베딩 모델: {settings.LLM_EMBEDDING_MODEL}")

    # 원본 데이터 로드
    print("원본 데이터 로드 중...")
    case_data = load_case_data()
    print(f"케이스 수: {len(case_data)}개")

    # 전략 목록
    if strategy == "all":
        strategies = list(VALID_STRATEGIES)
        print(f"\n전략 비교 모드: {', '.join(strategies)}")
    else:
        strategies = [strategy]

    # 전략별 평가 실행
    all_results = []
    for strat in strategies:
        result = run_single_strategy(strat, case_data, items, top_k)
        all_results.append(result)

    # 비교 테이블 출력 (all 모드)
    if len(all_results) > 1:
        print_comparison_table(all_results, top_k)

    # 결과 저장
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        result_filename = f"{output_name}.json"
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        strat_label = strategy if strategy != "all" else "all"
        result_filename = f"{timestamp}_{strat_label}.json"

    result_path = RESULTS_DIR / result_filename

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "strategy": strategy,
            "top_k": top_k,
            "embedding_model": settings.LLM_EMBEDDING_MODEL,
            "num_items": len(items),
            "num_cases": len(case_data),
        },
        "results": [
            {
                "strategy": r["strategy"],
                "summary": r["summary"],
                "aggregated": r["aggregated"],
                "build_time_ms": r["build_time_ms"],
                "details": r["details"],
            }
            for r in all_results
        ],
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {result_path}")


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="R2 승인 사례 RAG 평가")
    parser.add_argument(
        "--strategy",
        type=str,
        default="structured",
        choices=[*VALID_STRATEGIES, "all"],
        help="데이터 전략 (기본: structured, all=전체 비교)",
    )
    parser.add_argument(
        "--top_k", type=int, default=5, help="Top-K 값 (기본: 5)"
    )
    parser.add_argument(
        "--output", type=str, default=None, help="결과 파일명"
    )

    args = parser.parse_args()
    run_evaluation(
        strategy=args.strategy,
        top_k=args.top_k,
        output_name=args.output,
    )


if __name__ == "__main__":
    main()
