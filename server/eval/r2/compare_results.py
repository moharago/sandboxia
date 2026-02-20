"""R2 평가 결과 비교 스크립트

여러 실험 결과 JSON을 로드하여 비교표를 출력합니다.

실행:
    cd server
    uv run python eval/r2/compare_results.py                            # 전체 비교
    uv run python eval/r2/compare_results.py --filter strategy          # change_factor 필터
    uv run python eval/r2/compare_results.py --tag baseline             # 태그 필터
    uv run python eval/r2/compare_results.py --files file1.json file2.json  # 특정 파일만
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RESULTS_DIR = Path(__file__).parent / "results" / "retrieval"

METRICS_ROWS = [
    ("MH-Recall@K", "must_have_recall_at_k", False),
    ("Recall@K", "recall_at_k", False),
    ("MRR", "mrr", False),
    ("Negative@K", "negative_at_k", True),
    ("Neg Items", "items_with_negative", True),
    ("Latency P50", "latency_p50_ms", True),
    ("Latency P95", "latency_p95_ms", True),
    ("Build Time", "build_time_ms", True),
]


def load_experiment(path: Path) -> dict | None:
    """실험 결과 JSON 로드 (새 포맷만 지원)

    파일 I/O 또는 JSON 파싱 실패 시 에러를 기록하고 None을 반환하여
    load_all_experiments 루프가 중단되지 않도록 한다.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [ERROR] 파일 로드 실패: {path} ({type(e).__name__}: {e})")
        return None
    except Exception as e:
        print(f"  [ERROR] 예상치 못한 오류: {path} ({type(e).__name__}: {e})")
        return None

    # 새 포맷 검증: experiment 블록 필요
    if "experiment" not in data:
        return None

    return data


def load_all_experiments(
    filter_factor: str | None = None,
    filter_tag: str | None = None,
    file_paths: list[str] | None = None,
) -> list[dict]:
    """결과 디렉토리에서 실험 결과 로드

    Args:
        filter_factor: change_factor 필터 (예: "strategy")
        filter_tag: 태그 필터 (예: "baseline")
        file_paths: 특정 파일 경로 목록 (지정 시 다른 필터 무시)

    Returns:
        실험 결과 리스트 (날짜순 정렬)
    """
    experiments = []

    if file_paths:
        paths = [Path(p) if Path(p).is_absolute() else RESULTS_DIR / p for p in file_paths]
    else:
        if not RESULTS_DIR.exists():
            return []
        paths = sorted(RESULTS_DIR.glob("*.json"))

    for path in paths:
        if not path.exists():
            print(f"  [WARN] 파일 없음: {path}")
            continue

        exp = load_experiment(path)
        if exp is None:
            continue

        # 필터 적용
        if filter_factor and exp["experiment"].get("change_factor") != filter_factor:
            continue
        if filter_tag and filter_tag not in exp["experiment"].get("tags", []):
            continue

        exp["_filename"] = path.name
        experiments.append(exp)

    # 날짜 + id 순 정렬
    experiments.sort(key=lambda e: e["experiment"]["id"])
    return experiments


def format_value(key: str, value) -> str:
    """지표 값을 포맷팅"""
    if value is None:
        return "N/A"
    if key in ("latency_p50_ms", "latency_p95_ms", "latency_mean_ms", "build_time_ms"):
        return f"{value:.0f}ms"
    if key == "items_with_negative":
        return str(int(value))
    return f"{value:.4f}"


def print_comparison_table(experiments: list[dict]):
    """비교표 출력"""
    if not experiments:
        print("비교할 실험 결과가 없습니다.")
        return

    # 컬럼 너비 계산
    label_width = 15
    col_width = max(20, max(len(e["experiment"]["id"]) for e in experiments) + 2)

    # 헤더
    print("\n" + "=" * (label_width + col_width * len(experiments) + 2))
    print("R2 실험 결과 비교")
    print("=" * (label_width + col_width * len(experiments) + 2))

    # 실험 ID 행
    header = f"{'':>{label_width}}"
    for exp in experiments:
        exp_id = exp["experiment"]["id"]
        header += f"  {exp_id:>{col_width - 2}}"
    print(header)

    # 설명 행
    desc_row = f"{'':>{label_width}}"
    for exp in experiments:
        desc = exp["experiment"].get("description", "")
        if len(desc) > col_width - 2:
            desc = desc[: col_width - 5] + "..."
        desc_row += f"  {desc:>{col_width - 2}}"
    print(desc_row)

    print("─" * (label_width + col_width * len(experiments) + 2))

    # config 요약 (strategy, data_version)
    for config_key in ("strategy", "data_version", "embedding_model"):
        values = [exp["config"].get(config_key, "N/A") for exp in experiments]
        if len(set(values)) > 1:  # 다른 값이 있을 때만 표시
            row = f"{config_key:>{label_width}}"
            for v in values:
                row += f"  {str(v):>{col_width - 2}}"
            print(row)

    print("─" * (label_width + col_width * len(experiments) + 2))

    # 지표 행
    for label, key, lower_is_better in METRICS_ROWS:
        values = [exp["summary"].get(key) for exp in experiments]
        numeric_values = [v for v in values if v is not None]

        # 최고 성능 인덱스 계산
        best_idx = None
        if len(numeric_values) > 1:
            if lower_is_better:
                best_val = min(numeric_values)
            else:
                best_val = max(numeric_values)
            for i, v in enumerate(values):
                if v == best_val:
                    best_idx = i
                    break

        row = f"{label:>{label_width}}"
        for i, v in enumerate(values):
            formatted = format_value(key, v)
            marker = " *" if i == best_idx else "  "
            row += f"  {formatted + marker:>{col_width - 2}}"
        print(row)

    print("─" * (label_width + col_width * len(experiments) + 2))
    print("  * = 해당 지표 최고 성능 (Negative/Latency/Build Time: 낮을수록 좋음)")

    # 태그 정보
    tags_row = f"{'tags':>{label_width}}"
    for exp in experiments:
        tag_str = ", ".join(exp["experiment"].get("tags", []))
        tags_row += f"  {tag_str:>{col_width - 2}}"
    print(tags_row)


def print_per_item_diff(experiments: list[dict]):
    """항목별 차이 출력 (2개 실험 비교 시)"""
    if len(experiments) != 2:
        return

    exp_a, exp_b = experiments
    details_a = {d["id"]: d for d in exp_a["details"]}
    details_b = {d["id"]: d for d in exp_b["details"]}

    diffs = []
    for item_id in details_a:
        if item_id not in details_b:
            continue
        da, db = details_a[item_id], details_b[item_id]
        mh_diff = db["must_have_recall_at_k"] - da["must_have_recall_at_k"]
        r_diff = db["recall_at_k"] - da["recall_at_k"]
        if abs(mh_diff) > 0.001 or abs(r_diff) > 0.001:
            diffs.append((item_id, da, db, mh_diff, r_diff))

    if not diffs:
        print("\n항목별 차이 없음.")
        return

    diffs.sort(key=lambda x: x[3])  # MH-Recall diff 순

    id_a = exp_a["experiment"]["id"]
    id_b = exp_b["experiment"]["id"]
    print(f"\n항목별 변화 ({id_a} -> {id_b}):")
    print(f"{'ID':>10}  {'MH-R (A)':>8}  {'MH-R (B)':>8}  {'diff':>6}  {'R (A)':>8}  {'R (B)':>8}  {'diff':>6}")
    print("─" * 70)

    for item_id, da, db, mh_diff, r_diff in diffs:
        sign_mh = "+" if mh_diff > 0 else ""
        sign_r = "+" if r_diff > 0 else ""
        print(
            f"{item_id:>10}  "
            f"{da['must_have_recall_at_k']:>8.2f}  "
            f"{db['must_have_recall_at_k']:>8.2f}  "
            f"{sign_mh}{mh_diff:>5.2f}  "
            f"{da['recall_at_k']:>8.2f}  "
            f"{db['recall_at_k']:>8.2f}  "
            f"{sign_r}{r_diff:>5.2f}"
        )

    improved = sum(1 for _, _, _, mh, _ in diffs if mh > 0)
    regressed = sum(1 for _, _, _, mh, _ in diffs if mh < 0)
    print(f"\n  개선: {improved}건, 회귀: {regressed}건, 변동 합계: {len(diffs)}건")


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(description="R2 평가 결과 비교")
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="change_factor 필터 (예: strategy, data, embedding)",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="태그 필터 (예: baseline)",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="비교할 파일 목록 (파일명 또는 절대경로)",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="2개 실험의 항목별 차이 출력",
    )

    args = parser.parse_args()

    experiments = load_all_experiments(
        filter_factor=args.filter,
        filter_tag=args.tag,
        file_paths=args.files,
    )

    if not experiments:
        print("비교할 실험 결과가 없습니다.")
        print(f"결과 디렉토리: {RESULTS_DIR}")
        return

    print(f"로드된 실험: {len(experiments)}개")
    for exp in experiments:
        print(f"  - {exp['_filename']}")

    print_comparison_table(experiments)

    if args.diff and len(experiments) == 2:
        print_per_item_diff(experiments)
    elif args.diff and len(experiments) != 2:
        print("\n[WARN] --diff 옵션은 정확히 2개 실험 비교 시만 사용 가능합니다.")


if __name__ == "__main__":
    main()
