"""R1 규제제도 & 절차 RAG LLM-as-Judge 평가 스크립트

RAGAS 라이브러리를 사용하여 Generation 품질을 평가합니다.

평가 지표:
- Faithfulness: 응답이 컨텍스트에 기반하는지 (환각 방지)
- Response Relevancy: 응답이 질문에 적절히 답변하는지

실행:
    cd server
    uv run python eval/r1/run_llm_evaluation.py

옵션:
    --top_k 10        # Top-K 값 변경 (기본: 5)
    --output result   # 결과 파일명 (기본: 타임스탬프)
    --limit 5         # 평가 항목 수 제한 (테스트용)
    --trace           # LangSmith 추적 활성화 (토큰/비용 확인)
    --config E2       # 임베딩 설정 (없으면 .env 사용)
    --collection_suffix _E2  # 컬렉션 접미사

Judge 모델: gpt-4.1 (고정)
"""

import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def enable_langsmith_tracing(project_name: str = "rag-eval-r1") -> bool:
    """LangSmith 추적 활성화

    Args:
        project_name: LangSmith 프로젝트 이름

    Returns:
        True if enabled, False if API key not found
    """
    # .env에서 LANGCHAIN_API_KEY 확인
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("⚠️  LANGCHAIN_API_KEY가 .env에 없습니다. --trace 무시됨.")
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    return True


from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.constants import COLLECTION_REGULATIONS
from app.rag.config import EmbeddingConfig, load_embedding_config
from eval.llm_metrics import LLMMetricsResult, RAGASEvaluator, aggregate_llm_metrics
from eval.metrics import RetrievalMetrics, aggregate_metrics
from eval.r1.common import (
    RESULTS_DIR_LLM,
    build_gold_chunk_ids,
    calculate_retrieval_metrics,
    extract_chunk_id_from_doc,
    get_vector_store,
    load_evaluation_set,
)


GENERATION_MODEL = "gpt-4o-mini"  # 응답 생성 모델
JUDGE_MODEL = "gpt-4.1"  # LLM-as-Judge 모델 (고정)


def get_llm(model: str = GENERATION_MODEL) -> ChatOpenAI:
    """LLM 인스턴스 생성"""
    return ChatOpenAI(
        model=model,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )


async def generate_response(llm: ChatOpenAI, question: str, contexts: list[str]) -> str:
    """컨텍스트 기반 응답 생성"""
    context_text = "\n\n".join(contexts)

    prompt = f"""다음 규제샌드박스 제도 관련 정보를 참고하여 질문에 답변해주세요.

## 참고 정보:
{context_text}

## 질문:
{question}

## 답변:
위 정보를 바탕으로 간결하고 정확하게 답변해주세요."""

    response = await llm.ainvoke(prompt)
    return str(response.content)


async def evaluate_single_item(
    vector_store,
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
    gold_chunks = item.get("gold_chunks", [])

    # gold ID 생성
    gold_ids, must_have_ids = build_gold_chunk_ids(gold_chunks)

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
    detail = {
        "id": item["id"],
        "category": item.get("category", ""),
        "track": item.get("track", ""),
        "question": question,
        "response": response,
        "contexts": contexts[:3],  # 상위 3개만 저장
        "gold_ids": gold_ids,
        "retrieved_ids": retrieved_ids[:top_k],
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
    limit: int | None = None,
    embedding_config: EmbeddingConfig | None = None,
    collection_suffix: str = "",
):
    """전체 평가 실행 (비동기)"""
    print("=" * 70)
    print("R1 규제제도 & 절차 RAG 평가 (Retrieval + LLM-as-Judge)")
    print("=" * 70)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("questions", [])

    if limit:
        items = items[:limit]
        print(f"\n⚠️  평가 항목 제한: {limit}개")

    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    if embedding_config:
        print(f"임베딩: {embedding_config.name} ({embedding_config.model})")
    else:
        print(f"임베딩: .env 기본값 ({settings.LLM_EMBEDDING_MODEL})")
    print(f"컬렉션: {COLLECTION_REGULATIONS}{collection_suffix}")
    print(f"Generation Model: {GENERATION_MODEL}")
    print(f"Judge Model: {JUDGE_MODEL}")

    # 초기화
    print("\n초기화 중...")
    vector_store = get_vector_store(embedding_config, collection_suffix)
    llm = get_llm()
    evaluator = RAGASEvaluator(model=JUDGE_MODEL, api_key=settings.OPENAI_API_KEY)

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
        faith_str = f"{llm_metrics.faithfulness:.2f}" if llm_metrics.faithfulness is not None else "N/A"
        rel_str = f"{llm_metrics.answer_relevancy:.2f}" if llm_metrics.answer_relevancy is not None else "N/A"

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

    print(f"\n🤖 LLM-as-Judge 지표 ({JUDGE_MODEL}):")
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

    print("\n⏱️  Latency:")
    print(f"  - Retrieval P50: {retrieval_p50:.1f}ms | P95: {retrieval_p95:.1f}ms")
    print(f"  - Generation P50: {generation_p50:.1f}ms | P95: {generation_p95:.1f}ms")

    # 결과 저장
    RESULTS_DIR_LLM.mkdir(parents=True, exist_ok=True)

    if output_name:
        result_filename = f"{output_name}.json"
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        result_filename = f"{timestamp}.json"

    result_path = RESULTS_DIR_LLM / result_filename

    result_data = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "top_k": top_k,
            "embedding_config": embedding_config.name if embedding_config else ".env",
            "embedding_model": embedding_config.model if embedding_config else settings.LLM_EMBEDDING_MODEL,
            "embedding_provider": embedding_config.provider if embedding_config else "openai",
            "judge_model": JUDGE_MODEL,
            "generation_model": GENERATION_MODEL,
            "collection": COLLECTION_REGULATIONS + collection_suffix,
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
    limit: int | None = None,
    embedding_config: EmbeddingConfig | None = None,
    collection_suffix: str = "",
):
    """전체 평가 실행 (동기 래퍼)"""
    asyncio.run(
        run_evaluation_async(
            top_k=top_k,
            output_name=output_name,
            limit=limit,
            embedding_config=embedding_config,
            collection_suffix=collection_suffix,
        )
    )


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(
        description="R1 규제제도 & 절차 RAG 평가 (Retrieval + LLM-as-Judge)"
    )
    parser.add_argument("--top_k", type=int, default=5, help="Top-K 값 (기본: 5)")
    parser.add_argument("--output", type=str, default=None, help="결과 파일명")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="평가 항목 수 제한 (테스트용)",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="LangSmith 추적 활성화 (토큰/비용 확인)",
    )
    parser.add_argument("--config", type=str, default=None, help="임베딩 설정 (없으면 .env 사용)")
    parser.add_argument("--collection_suffix", type=str, default="", help="컬렉션 접미사")

    args = parser.parse_args()

    # LangSmith 추적 활성화 (--trace 플래그 사용 시)
    if args.trace:
        if enable_langsmith_tracing("rag-eval-r1"):
            print("📊 LangSmith 추적 활성화됨 (https://smith.langchain.com)")

    # 임베딩 설정 로드 (프리셋 지정 시에만)
    embedding_config = None
    if args.config:
        embedding_config = load_embedding_config(args.config, rag_type="r1")

    run_evaluation(
        top_k=args.top_k,
        output_name=args.output,
        limit=args.limit,
        embedding_config=embedding_config,
        collection_suffix=args.collection_suffix,
    )


if __name__ == "__main__":
    main()
