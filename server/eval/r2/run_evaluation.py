"""R2 승인 사례 RAG 평가 스크립트

전략별 Retrieval 성능을 비교합니다. 1파일 = 1실험 원칙.

평가 지표:
- Must-Have Recall@K: 핵심 사례(must_have=true) 검색률
- Recall@K: 전체 gold_cases 검색률
- MRR: 첫 번째 정답 사례의 역순위
- Negative@K: 검색되면 안 되는 사례 포함 비율 (낮을수록 좋음)
- Latency (P50): 검색 응답 시간

실행:
    cd server
    uv run python eval/r2/run_evaluation.py                    # structured만
    uv run python eval/r2/run_evaluation.py --strategy all     # 3개 전략 비교 (각각 파일 저장)
    uv run python eval/r2/run_evaluation.py --embedding E1     # 임베딩 모델 지정
    uv run python eval/r2/run_evaluation.py --embedding all --data-version enriched --tags stage2

옵션:
    --strategy structured|hybrid|fulltext|all  (기본: structured)
    --embedding E0|E1|E4|E5|all                (임베딩 프리셋, eval/r2/configs/embedding.yaml)
    --top_k 10                                 (기본: 5)
    --threshold 0.3                            (score threshold, 기본: None = 필터 없음)
    --output result                            (결과 파일명, 기본: 자동 생성)
    --change-factor strategy                   (이번 실험에서 바꾼 변수)
    --change-value structured                  (해당 변수의 값)
    --data-version original                    (original | enriched)
    --tags baseline                            (쉼표 구분 태그)
    --description "1단계: 데이터 전략 비교"    (실험 설명)
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
from app.rag.config import EmbeddingConfig, list_configs
from eval.r2.common import (
    RESULTS_DIR,
    VALID_STRATEGIES,
    build_gold_case_ids,
    calculate_r2_metrics,
    create_temp_vector_store,
    extract_case_id_from_result,
    load_case_data,
    load_evaluation_set,
    load_r2_embedding_config,
)


def evaluate_single_item(
    vectorstore,
    item: dict,
    top_k: int = 5,
    threshold: float | None = None,
) -> tuple[RetrievalMetrics, float, float, dict]:
    """단일 평가 항목 평가

    Args:
        vectorstore: Chroma Vector Store
        item: 평가 항목
        top_k: Top-K 값
        threshold: Score threshold (None이면 필터 없음)

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
    if threshold is not None:
        results_with_scores = vectorstore.similarity_search_with_relevance_scores(
            question, k=top_k
        )
        filtered = [
            (doc, score)
            for doc, score in results_with_scores
            if score >= threshold
        ]
        results = [doc for doc, _ in filtered]
        scores = [round(score, 4) for _, score in filtered]
    else:
        results = vectorstore.similarity_search(question, k=top_k)
        scores = None
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
        "scores": scores,
        "actual_k": len(retrieved_ids),
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
    embedding_config: EmbeddingConfig | None = None,
    threshold: float | None = None,
) -> dict:
    """단일 전략 평가 실행

    Args:
        strategy: 데이터 전략
        case_data: 원본 케이스 데이터
        eval_items: 평가 항목 리스트
        top_k: Top-K 값
        embedding_config: 임베딩 설정 (None이면 기본 모델)

    Returns:
        전략 평가 결과 dict
    """
    emb_label = embedding_config.name if embedding_config else "default"
    threshold_label = f" | threshold: {threshold}" if threshold is not None else ""
    print(f"\n{'─' * 60}")
    print(f"전략: {strategy} | 임베딩: {emb_label}{threshold_label}")
    print(f"{'─' * 60}")

    # 임시 Vector Store 생성
    print(f"  Vector Store 생성 중 ({strategy}, {emb_label})...")
    collection_name = f"r2_eval_{strategy}_{emb_label}"

    build_start = time.perf_counter()
    vectorstore, client = create_temp_vector_store(
        case_data, strategy, collection_name, embedding_config
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
            vectorstore, item, top_k, threshold
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
        "embedding_label": emb_label,
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
    """전략/임베딩 비교 테이블 출력"""
    print("\n" + "=" * 70)
    print("비교 결과")
    print("=" * 70)

    # 헤더: 전략+임베딩 조합 표시
    header = f"{'지표':<25}"
    for r in results:
        label = r.get("embedding_label", "default")
        col = f"{r['strategy']}({label})" if label != "default" else r["strategy"]
        header += f"  {col:>14}"
    print(header)
    print("─" * (25 + 16 * len(results)))

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


def build_experiment_json(
    result: dict,
    *,
    num_cases: int,
    num_eval_items: int,
    top_k: int,
    change_factor: str,
    change_value: str,
    data_version: str,
    tags: list[str],
    description: str,
    embedding_config: EmbeddingConfig | None = None,
    threshold: float | None = None,
) -> dict:
    """단일 실험 결과를 새 JSON 포맷으로 구성

    Args:
        result: run_single_strategy()의 리턴값
        num_cases: 전체 케이스 수
        num_eval_items: 평가 항목 수
        top_k: Top-K 값
        change_factor: 이번 실험에서 바꾼 변수
        change_value: 해당 변수의 값
        data_version: 데이터 버전 (original / enriched)
        tags: 그룹핑용 태그
        description: 실험 설명
        embedding_config: 임베딩 설정 (None이면 settings 사용)

    Returns:
        새 포맷 JSON dict
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    experiment_id = f"{date_str}_{change_factor}_{change_value}"
    embedding_model_name = embedding_config.model if embedding_config else settings.LLM_EMBEDDING_MODEL

    summary = dict(result["summary"])
    summary["build_time_ms"] = result["build_time_ms"]

    return {
        "experiment": {
            "id": experiment_id,
            "date": date_str,
            "timestamp": now.isoformat(timespec="seconds"),
            "description": description,
            "change_factor": change_factor,
            "change_value": change_value,
            "tags": tags,
        },
        "config": {
            "strategy": result["strategy"],
            "embedding_model": embedding_model_name,
            "top_k": top_k,
            "threshold": threshold,
            "num_cases": num_cases,
            "num_eval_items": num_eval_items,
            "data_version": data_version,
            "chunking": "none",
            "vector_db": "chroma_ephemeral",
        },
        "summary": summary,
        "aggregated": result["aggregated"],
        "details": result["details"],
    }


def save_experiment(experiment_data: dict, output_name: str | None = None) -> Path:
    """실험 결과를 파일로 저장

    Args:
        experiment_data: build_experiment_json()의 리턴값
        output_name: 수동 파일명 (없으면 experiment.id 사용)

    Returns:
        저장된 파일 경로
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        filename = f"{output_name}.json"
    else:
        filename = f"{experiment_data['experiment']['id']}.json"

    result_path = RESULTS_DIR / filename

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(experiment_data, f, ensure_ascii=False, indent=2)

    return result_path


def run_evaluation(
    strategy: str = "structured",
    top_k: int = 5,
    output_name: str | None = None,
    change_factor: str | None = None,
    change_value: str | None = None,
    data_version: str = "original",
    tags: list[str] | None = None,
    description: str = "",
    embedding: str | None = None,
    threshold: float | None = None,
):
    """전체 평가 실행

    Args:
        strategy: 데이터 전략 (structured / hybrid / fulltext / all)
        top_k: Top-K 값
        output_name: 결과 파일명 (없으면 자동 생성)
        change_factor: 이번 실험에서 바꾼 변수
        change_value: 해당 변수의 값
        data_version: 데이터 버전 (original / enriched)
        tags: 그룹핑용 태그
        description: 실험 설명
        embedding: 임베딩 프리셋명 (E0/E1/E4/E5/all, None이면 기본 모델)
    """
    print("=" * 60)
    print("R2 승인 사례 RAG 평가 시작")
    print("=" * 60)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("evaluation_items", [])
    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    if threshold is not None:
        print(f"Threshold: {threshold}")

    # 임베딩 설정 목록 구성
    if embedding == "all":
        available = list_configs(rag_type="r2").get("embedding", [])
        embedding_configs = [load_r2_embedding_config(name) for name in available]
        print(f"임베딩 비교 모드: {', '.join(available)}")
    elif embedding:
        embedding_configs = [load_r2_embedding_config(embedding.upper())]
        print(f"임베딩 모델: {embedding_configs[0].model} ({embedding_configs[0].name})")
    else:
        embedding_configs = [None]
        print(f"임베딩 모델: {settings.LLM_EMBEDDING_MODEL} (default)")

    # 데이터 로드
    print(f"데이터 로드 중... (version: {data_version})")
    case_data = load_case_data(data_version)
    print(f"케이스 수: {len(case_data)}개")

    # 전략 목록
    is_strategy_all = strategy == "all"
    if is_strategy_all:
        strategies = list(VALID_STRATEGIES)
        print(f"\n전략 비교 모드: {', '.join(strategies)}")
    else:
        strategies = [strategy]

    # change_factor/change_value 기본값 설정
    is_embedding_mode = embedding is not None
    if change_factor is None:
        change_factor = "embedding" if is_embedding_mode else "strategy"
    if change_value is None and not is_embedding_mode:
        change_value = strategy
    if tags is None:
        tags = []

    # 전략 × 임베딩 조합 평가
    all_results = []
    saved_paths = []

    for emb_config in embedding_configs:
        for strat in strategies:
            result = run_single_strategy(
                strat, case_data, items, top_k, emb_config, threshold
            )
            all_results.append((result, emb_config))

    # 비교 테이블 출력 (복수 결과)
    if len(all_results) > 1:
        print_comparison_table([r for r, _ in all_results], top_k)

    # 결과 저장 (1파일 = 1실험)
    for result, emb_config in all_results:
        # change_value 결정
        if is_embedding_mode and emb_config:
            cv = change_value or emb_config.name
        elif is_strategy_all:
            cv = result["strategy"]
        else:
            cv = change_value or strategy

        desc = description
        if not desc:
            if emb_config:
                desc = f"임베딩: {emb_config.model} ({emb_config.name})"
            else:
                desc = f"전략: {result['strategy']}"

        experiment_data = build_experiment_json(
            result,
            num_cases=len(case_data),
            num_eval_items=len(items),
            top_k=top_k,
            change_factor=change_factor,
            change_value=cv,
            data_version=data_version,
            tags=tags,
            description=desc,
            embedding_config=emb_config,
            threshold=threshold,
        )

        out = output_name if len(all_results) == 1 else None
        path = save_experiment(experiment_data, out)
        saved_paths.append(path)

    print(f"\n결과 저장 ({len(saved_paths)}개 파일):")
    for p in saved_paths:
        print(f"  {p}")


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
        "--embedding",
        type=str,
        default=None,
        help="임베딩 프리셋 (E0/E1/E4/E5/all, eval/r2/configs/embedding.yaml 참조)",
    )
    parser.add_argument(
        "--top_k", type=int, default=5, help="Top-K 값 (기본: 5)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Score threshold (기본: None = 필터 없음, 예: 0.3)",
    )
    parser.add_argument(
        "--output", type=str, default=None, help="결과 파일명 (단일 전략만)"
    )
    parser.add_argument(
        "--change-factor",
        type=str,
        default=None,
        help="이번 실험에서 바꾼 변수 (기본: strategy)",
    )
    parser.add_argument(
        "--change-value",
        type=str,
        default=None,
        help="해당 변수의 값 (기본: --strategy 값)",
    )
    parser.add_argument(
        "--data-version",
        type=str,
        default="original",
        choices=["original", "enriched"],
        help="데이터 버전 (기본: original)",
    )
    parser.add_argument(
        "--tags",
        type=str,
        default="",
        help="쉼표 구분 태그 (예: baseline,v1)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="실험 설명",
    )

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    run_evaluation(
        strategy=args.strategy,
        top_k=args.top_k,
        output_name=args.output,
        change_factor=args.change_factor,
        change_value=args.change_value,
        data_version=args.data_version,
        tags=tags,
        description=args.description,
        embedding=args.embedding,
        threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
