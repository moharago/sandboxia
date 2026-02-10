"""R3 법령 RAG 평가 스크립트

평가 지표:
- Must-Have Recall@5: 핵심 조항(must_have=true) 검색률
- Recall@5: 전체 gold_citations 검색률
- MRR: 첫 번째 정답 조항의 역순위
- Latency (P50): 검색 응답 시간

실행:
    cd server
    uv run python eval/r3/run_evaluation.py

옵션:
    --top_k 10        # Top-K 값 변경 (기본: 5)
    --output result   # 결과 파일명 (기본: 타임스탬프)
"""

import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from eval.metrics import RetrievalMetrics, aggregate_metrics

# 경로 설정
EVAL_DIR = Path(__file__).parent
EVALUATION_SET_PATH = EVAL_DIR / "evaluation_set.json"
RESULTS_DIR = EVAL_DIR / "results"


def load_evaluation_set() -> dict:
    """평가셋 로드"""
    with open(EVALUATION_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_vector_store() -> Chroma:
    """Vector Store 연결

    기존 Vector Store에 연결하여 검색 수행.
    쿼리 임베딩을 위해 embedding_function이 필요함.
    """
    embeddings = OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )

    return Chroma(
        collection_name=COLLECTION_LAWS,
        embedding_function=embeddings,
        persist_directory=str(settings.CHROMA_PERSIST_DIR),
    )


def build_gold_chunk_ids(
    gold_citations: list[dict],
) -> tuple[list[str], list[str]]:
    """gold_citations에서 매칭용 ID 생성

    매칭 키: (law_name, article_no, paragraph_no)
    - article_title은 같은 조에 여러 조항이 있는 경우에만 구분용으로 사용

    Returns:
        (all_gold_ids, must_have_ids)
    """
    all_ids = []
    must_have_ids = []

    for citation in gold_citations:
        # 기본 매칭 키: law_name, article_no, paragraph_no
        base_id = f"{citation.get('law_name', '')}|{citation.get('article_no', '')}|{citation.get('paragraph_no', '')}"

        # article_title이 있으면 추가 (같은 조에 여러 조항이 있는 경우 구분)
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
    """Document에서 매칭용 chunk_id 추출"""
    meta = doc.metadata
    base_id = f"{meta.get('law_name', '')}|{meta.get('article_no', '')}|{meta.get('paragraph_no', '')}"
    article_title = meta.get("article_title", "")

    return {
        "base_id": base_id,
        "article_title": article_title,
    }


def match_ids(retrieved_id: dict, gold_id: dict) -> bool:
    """두 ID가 매칭되는지 확인

    매칭 규칙:
    1. base_id (law_name, article_no, paragraph_no) 필수 일치
    2. gold_id에 article_title이 있으면 추가로 일치해야 함
    """
    if retrieved_id["base_id"] != gold_id["base_id"]:
        return False

    # gold에 article_title이 있으면 검증
    if gold_id["article_title"]:
        return retrieved_id["article_title"] == gold_id["article_title"]

    return True


def calculate_metrics_with_matching(
    retrieved_ids: list[dict],
    gold_ids: list[dict],
    must_have_ids: list[dict],
    k: int,
) -> RetrievalMetrics:
    """매칭 로직을 적용한 지표 계산

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


def evaluate_single_item(
    vector_store: Chroma,
    item: dict,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, float, dict]:
    """단일 평가 항목 평가

    Args:
        vector_store: Vector Store
        item: 평가 항목
        top_k: Top-K 값

    Returns:
        (metrics, latency_ms, detail_info)
    """
    question = item["question"]
    gold_citations = item.get("gold_citations", [])

    # gold ID 생성
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_citations)

    # 검색 실행 (시간 측정)
    start_time = time.perf_counter()
    results = vector_store.similarity_search(question, k=top_k)
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000

    # 검색 결과에서 chunk_id 추출
    retrieved_ids = [extract_chunk_id_from_doc(doc) for doc in results]

    # 지표 계산 (커스텀 매칭 로직 적용)
    metrics = calculate_metrics_with_matching(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        k=top_k,
    )

    # 상세 정보 (읽기 쉬운 형식으로 변환)
    gold_ids_str = [f"{g['base_id']}|{g['article_title']}" if g["article_title"] else g["base_id"] for g in gold_ids]
    must_have_ids_str = [f"{g['base_id']}|{g['article_title']}" if g["article_title"] else g["base_id"] for g in must_have_ids]
    retrieved_ids_str = [f"{r['base_id']}|{r['article_title']}" if r["article_title"] else r["base_id"] for r in retrieved_ids[:top_k]]

    detail = {
        "id": item["id"],
        "domain": item.get("domain", ""),
        "question": question,
        "gold_ids": gold_ids_str,
        "must_have_ids": must_have_ids_str,
        "retrieved_ids": retrieved_ids_str,
        "recall_at_k": metrics.recall_at_k,
        "must_have_recall_at_k": metrics.must_have_recall_at_k,
        "mrr": metrics.mrr,
        "first_hit_rank": metrics.first_hit_rank,
        "latency_ms": round(latency_ms, 2),
    }

    return metrics, latency_ms, detail


def run_evaluation(top_k: int = 5, output_name: str | None = None):
    """전체 평가 실행

    Args:
        top_k: Top-K 값
        output_name: 결과 파일명 (없으면 타임스탬프 사용)
    """
    print("=" * 60)
    print("R3 법령 RAG 평가 시작")
    print("=" * 60)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("evaluation_items", [])
    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")

    # Vector Store 초기화
    print("\nVector Store 초기화 중...")
    vector_store = get_vector_store()

    # 평가 실행
    print("\n평가 진행 중...\n")
    all_metrics: list[RetrievalMetrics] = []
    all_latencies: list[float] = []
    all_details: list[dict] = []

    for i, item in enumerate(items, 1):
        metrics, latency, detail = evaluate_single_item(vector_store, item, top_k)
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

    # Latency 통계
    latency_p50 = statistics.median(all_latencies)
    latency_p95 = (
        sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        if len(all_latencies) >= 20
        else max(all_latencies)
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

    print(f"\n⏱️  Latency:")
    print(f"  - P50: {latency_p50:.1f}ms")
    print(f"  - P95: {latency_p95:.1f}ms")
    print(f"  - Mean: {latency_mean:.1f}ms")

    print(f"\n📈 세부 통계:")
    print(f"  - 총 gold_citations: {aggregated['total_gold_citations']}")
    print(f"  - 검색된 gold: {aggregated['total_retrieved_gold']}")
    print(f"  - 총 must_have: {aggregated['total_must_have_citations']}")
    print(f"  - 검색된 must_have: {aggregated['total_must_have_retrieved']}")

    # 결과 저장
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        result_filename = f"{output_name}.json"
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        result_filename = f"{timestamp}.json"

    result_path = RESULTS_DIR / result_filename

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "top_k": top_k,
            "embedding_model": settings.LLM_EMBEDDING_MODEL,
            "collection": COLLECTION_LAWS,
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

    args = parser.parse_args()

    run_evaluation(top_k=args.top_k, output_name=args.output)


if __name__ == "__main__":
    main()
