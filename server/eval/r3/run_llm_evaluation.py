"""R3 법령 RAG LLM-as-Judge 평가 스크립트

RAGAS 라이브러리를 사용하여 Generation 품질을 평가합니다.

평가 지표:
- Faithfulness: 응답이 컨텍스트에 기반하는지 (환각 방지)
- Response Relevancy: 응답이 질문에 적절히 답변하는지

실행:
    cd server
    uv run python eval/r3/run_llm_evaluation.py

옵션:
    --top_k 10        # Top-K 값 변경 (기본: 5)
    --output result   # 결과 파일명 (기본: 타임스탬프)
    --model gpt-4o    # 평가 LLM 모델 (기본: gpt-4o-mini)
    --limit 5         # 평가 항목 수 제한 (테스트용)
"""

import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from eval.llm_metrics import LLMMetricsResult, RAGASEvaluator, aggregate_llm_metrics
from eval.metrics import RetrievalMetrics, aggregate_metrics

# 경로 설정
EVAL_DIR = Path(__file__).parent
EVALUATION_SET_PATH = EVAL_DIR / "evaluation_set.json"
RESULTS_DIR = EVAL_DIR / "results" / "llm"


def load_evaluation_set() -> dict:
    """평가셋 로드"""
    with open(EVALUATION_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_vector_store() -> Chroma:
    """Vector Store 연결"""
    embeddings = OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )

    return Chroma(
        collection_name=COLLECTION_LAWS,
        embedding_function=embeddings,
        persist_directory=str(settings.CHROMA_PERSIST_DIR),
    )


def get_llm(model: str = "gpt-4o-mini") -> ChatOpenAI:
    """LLM 인스턴스 생성"""
    return ChatOpenAI(
        model=model,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )


def build_gold_chunk_ids(
    gold_citations: list[dict],
) -> tuple[list[dict], list[dict]]:
    """gold_citations에서 매칭용 ID 생성"""
    all_ids = []
    must_have_ids = []

    for citation in gold_citations:
        base_id = f"{citation.get('law_name', '')}|{citation.get('article_no', '')}|{citation.get('paragraph_no', '')}"
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
    """두 ID가 매칭되는지 확인"""
    if retrieved_id["base_id"] != gold_id["base_id"]:
        return False

    if gold_id["article_title"]:
        return retrieved_id["article_title"] == gold_id["article_title"]

    return True


def calculate_retrieval_metrics(
    retrieved_ids: list[dict],
    gold_ids: list[dict],
    must_have_ids: list[dict],
    k: int,
) -> RetrievalMetrics:
    """Retrieval 지표 계산"""
    top_k_retrieved = retrieved_ids[:k]

    # Recall@K
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

    # MRR
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


async def generate_response(llm: ChatOpenAI, question: str, contexts: list[str]) -> str:
    """컨텍스트 기반 응답 생성"""
    context_text = "\n\n".join(contexts)

    prompt = f"""다음 법령 조항들을 참고하여 질문에 답변해주세요.

## 참고 법령 조항:
{context_text}

## 질문:
{question}

## 답변:
위 법령 조항을 바탕으로 간결하고 정확하게 답변해주세요."""

    response = await llm.ainvoke(prompt)
    return str(response.content)


async def evaluate_single_item(
    vector_store: Chroma,
    llm: ChatOpenAI,
    evaluator: RAGASEvaluator,
    item: dict,
    top_k: int = 5,
) -> tuple[RetrievalMetrics, LLMMetricsResult, float, float, dict]:
    """단일 평가 항목 평가 (Retrieval + Generation)

    Returns:
        (retrieval_metrics, llm_metrics, retrieval_latency, generation_latency, detail_info)
    """
    question = item["question"]
    gold_citations = item.get("gold_citations", [])

    # gold ID 생성
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_citations)

    # 1. 검색 실행
    retrieval_start = time.perf_counter()
    results = vector_store.similarity_search(question, k=top_k)
    retrieval_end = time.perf_counter()
    retrieval_latency = (retrieval_end - retrieval_start) * 1000

    # 검색 결과에서 chunk_id와 content 추출
    retrieved_ids = [extract_chunk_id_from_doc(doc) for doc in results]
    contexts = [doc.page_content for doc in results]

    # Retrieval 지표 계산
    retrieval_metrics = calculate_retrieval_metrics(
        retrieved_ids=retrieved_ids,
        gold_ids=gold_ids,
        must_have_ids=must_have_ids,
        k=top_k,
    )

    # 2. 응답 생성
    generation_start = time.perf_counter()
    response = await generate_response(llm, question, contexts)
    generation_end = time.perf_counter()
    generation_latency = (generation_end - generation_start) * 1000

    # 3. LLM-as-Judge 평가
    llm_metrics = await evaluator.evaluate(
        question=question,
        response=response,
        contexts=contexts,
    )

    # 상세 정보
    gold_ids_str = [
        f"{g['base_id']}|{g['article_title']}" if g["article_title"] else g["base_id"]
        for g in gold_ids
    ]
    retrieved_ids_str = [
        f"{r['base_id']}|{r['article_title']}" if r["article_title"] else r["base_id"]
        for r in retrieved_ids[:top_k]
    ]

    detail = {
        "id": item["id"],
        "domain": item.get("domain", ""),
        "question": question,
        "response": response,
        "contexts": contexts[:3],  # 상위 3개만 저장
        "gold_ids": gold_ids_str,
        "retrieved_ids": retrieved_ids_str,
        # Retrieval 지표
        "recall_at_k": retrieval_metrics.recall_at_k,
        "must_have_recall_at_k": retrieval_metrics.must_have_recall_at_k,
        "mrr": retrieval_metrics.mrr,
        "retrieval_latency_ms": round(retrieval_latency, 2),
        # LLM 지표
        "faithfulness": llm_metrics.faithfulness,
        "answer_relevancy": llm_metrics.answer_relevancy,
        "generation_latency_ms": round(generation_latency, 2),
        # 오류
        "llm_error": llm_metrics.error,
    }

    return retrieval_metrics, llm_metrics, retrieval_latency, generation_latency, detail


async def run_evaluation_async(
    top_k: int = 5,
    output_name: str | None = None,
    judge_model: str = "gpt-4o-mini",
    limit: int | None = None,
):
    """전체 평가 실행 (비동기)"""
    print("=" * 70)
    print("R3 법령 RAG 평가 (Retrieval + LLM-as-Judge)")
    print("=" * 70)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("evaluation_items", [])

    if limit:
        items = items[:limit]
        print(f"\n⚠️  평가 항목 제한: {limit}개")

    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    print(f"Judge Model: {judge_model}")

    # 초기화
    print("\n초기화 중...")
    vector_store = get_vector_store()
    llm = get_llm()
    evaluator = RAGASEvaluator(model=judge_model)

    # 평가 실행
    print("\n평가 진행 중...\n")
    all_retrieval_metrics: list[RetrievalMetrics] = []
    all_llm_metrics: list[LLMMetricsResult] = []
    all_retrieval_latencies: list[float] = []
    all_generation_latencies: list[float] = []
    all_details: list[dict] = []

    for i, item in enumerate(items, 1):
        (
            retrieval_metrics,
            llm_metrics,
            retrieval_latency,
            generation_latency,
            detail,
        ) = await evaluate_single_item(
            vector_store, llm, evaluator, item, top_k
        )

        all_retrieval_metrics.append(retrieval_metrics)
        all_llm_metrics.append(llm_metrics)
        all_retrieval_latencies.append(retrieval_latency)
        all_generation_latencies.append(generation_latency)
        all_details.append(detail)

        # 진행 상황 출력
        faith_str = f"{llm_metrics.faithfulness:.2f}" if llm_metrics.faithfulness else "N/A"
        rel_str = f"{llm_metrics.answer_relevancy:.2f}" if llm_metrics.answer_relevancy else "N/A"

        print(
            f"  [{i:2d}/{len(items)}] {item['id']} | "
            f"Recall: {retrieval_metrics.recall_at_k:.2f} | "
            f"Faith: {faith_str} | "
            f"Rel: {rel_str} | "
            f"Gen: {generation_latency:.0f}ms"
        )

    # 집계
    retrieval_agg = aggregate_metrics(all_retrieval_metrics)
    llm_agg = aggregate_llm_metrics(all_llm_metrics)

    # Latency 통계
    retrieval_p50 = statistics.median(all_retrieval_latencies)
    retrieval_p95 = (
        sorted(all_retrieval_latencies)[int(len(all_retrieval_latencies) * 0.95)]
        if len(all_retrieval_latencies) >= 20
        else max(all_retrieval_latencies)
    )
    generation_p50 = statistics.median(all_generation_latencies)
    generation_p95 = (
        sorted(all_generation_latencies)[int(len(all_generation_latencies) * 0.95)]
        if len(all_generation_latencies) >= 20
        else max(all_generation_latencies)
    )

    # 결과 출력
    print("\n" + "=" * 70)
    print("평가 결과 요약")
    print("=" * 70)

    print(f"\n📊 Retrieval 지표 (K={top_k}):")
    print(f"  - Must-Have Recall@{top_k}: {retrieval_agg['avg_must_have_recall_at_k']:.4f}")
    print(f"  - Recall@{top_k}:           {retrieval_agg['avg_recall_at_k']:.4f}")
    print(f"  - MRR:                      {retrieval_agg['avg_mrr']:.4f}")

    print(f"\n🤖 LLM-as-Judge 지표 ({judge_model}):")
    if llm_agg.get("avg_faithfulness") is not None:
        print(f"  - Faithfulness:         {llm_agg['avg_faithfulness']:.4f}")
    else:
        print("  - Faithfulness:         N/A")
    if llm_agg.get("avg_answer_relevancy") is not None:
        print(f"  - Answer Relevancy:     {llm_agg['avg_answer_relevancy']:.4f}")
    else:
        print("  - Answer Relevancy:     N/A")

    if llm_agg.get("errors", 0) > 0:
        print(f"  - 평가 오류:            {llm_agg['errors']}건")

    print(f"\n⏱️  Latency:")
    print(f"  - Retrieval P50: {retrieval_p50:.1f}ms | P95: {retrieval_p95:.1f}ms")
    print(f"  - Generation P50: {generation_p50:.1f}ms | P95: {generation_p95:.1f}ms")

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
            "judge_model": judge_model,
            "generation_model": "gpt-4o-mini",
            "collection": COLLECTION_LAWS,
            "num_items": len(items),
        },
        "summary": {
            # Retrieval 지표
            "must_have_recall_at_k": retrieval_agg["avg_must_have_recall_at_k"],
            "recall_at_k": retrieval_agg["avg_recall_at_k"],
            "mrr": retrieval_agg["avg_mrr"],
            # LLM 지표
            "faithfulness": llm_agg.get("avg_faithfulness"),
            "answer_relevancy": llm_agg.get("avg_answer_relevancy"),
            # Latency
            "retrieval_latency_p50_ms": round(retrieval_p50, 2),
            "retrieval_latency_p95_ms": round(retrieval_p95, 2),
            "generation_latency_p50_ms": round(generation_p50, 2),
            "generation_latency_p95_ms": round(generation_p95, 2),
        },
        "retrieval_aggregated": retrieval_agg,
        "llm_aggregated": llm_agg,
        "details": all_details,
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 결과 저장: {result_path}")


def run_evaluation(
    top_k: int = 5,
    output_name: str | None = None,
    judge_model: str = "gpt-4o-mini",
    limit: int | None = None,
):
    """전체 평가 실행 (동기 래퍼)"""
    asyncio.run(
        run_evaluation_async(
            top_k=top_k,
            output_name=output_name,
            judge_model=judge_model,
            limit=limit,
        )
    )


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(
        description="R3 법령 RAG 평가 (Retrieval + LLM-as-Judge)"
    )
    parser.add_argument("--top_k", type=int, default=5, help="Top-K 값 (기본: 5)")
    parser.add_argument("--output", type=str, default=None, help="결과 파일명")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Judge LLM 모델 (기본: gpt-4o-mini)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="평가 항목 수 제한 (테스트용)",
    )

    args = parser.parse_args()

    run_evaluation(
        top_k=args.top_k,
        output_name=args.output,
        judge_model=args.model,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
