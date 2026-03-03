"""R2 승인 사례 RAG LLM-as-Judge 평가 스크립트

확정 조합(enriched + E0)으로 LLM 답변을 생성하고 생성 품질을 평가합니다.
생성 모델을 비교하여 최적 모델을 선택합니다.

평가 지표:
- Retrieval: Must-Have Recall@K, Recall@K, MRR, Negative@K (모델 무관, 1회만 측정)
- LLM-as-Judge: Faithfulness, Answer Relevancy (RAGAS, gpt-4.1)
- R2 고유: Must-Include Coverage, Must-Not-Include Violation, Bullet Coverage

실행:
    cd server
    uv run python eval/r2/run_llm_evaluation.py --limit 3 --tags test
    uv run python eval/r2/run_llm_evaluation.py --tags stage3
    uv run python eval/r2/run_llm_evaluation.py --model all --tags stage3
    uv run python eval/r2/run_llm_evaluation.py --model gpt-4.1-mini --tags stage3

옵션:
    --model gpt-4o-mini            생성 모델 (기본: gpt-4o-mini, all=전체 비교)
    --strategy structured          데이터 전략 (기본: structured)
    --embedding E0                 임베딩 프리셋 (기본: .env 기본값)
    --data-version enriched        데이터 버전 (기본: enriched)
    --top_k 5                      Top-K (기본: 5)
    --limit 3                      평가 항목 수 제한 (테스트용)
    --output result                결과 파일명 (단일 모델만)
    --change-factor generation_model  이번 실험에서 바꾼 변수
    --change-value gpt-4o-mini     해당 변수의 값
    --tags stage3                  쉼표 구분 태그
    --description "..."            실험 설명
    --trace                        LangSmith 추적
    --no-bullet-judge              Bullet Coverage LLM Judge 비활성화 (비용 절감)
"""

import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def enable_langsmith_tracing(project_name: str = "rag-eval-r2") -> bool:
    """LangSmith 추적 활성화"""
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("  LANGCHAIN_API_KEY가 .env에 없습니다. --trace 무시됨.")
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    return True


from app.core.config import settings
from app.rag.config import EmbeddingConfig
from eval.llm_metrics import LLMMetricsResult, RAGASEvaluator, aggregate_llm_metrics
from eval.metrics import RetrievalMetrics, aggregate_metrics
from eval.r2.common import (
    RESULTS_DIR_LLM,
    TEMP_COLLECTION_NAME,
    VALID_STRATEGIES,
    build_gold_case_ids,
    calculate_r2_metrics,
    create_temp_vector_store,
    extract_case_id_from_result,
    load_case_data,
    load_evaluation_set,
    load_r2_embedding_config,
)

# ---------------------------------------------------------------------------
# 모델 설정
# ---------------------------------------------------------------------------

GENERATION_MODELS = [
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4.1",
]
DEFAULT_GENERATION_MODEL = "gpt-4o-mini"
JUDGE_MODEL = "gpt-4.1"


# ---------------------------------------------------------------------------
# LLM 및 생성
# ---------------------------------------------------------------------------


def get_llm(model: str = DEFAULT_GENERATION_MODEL) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )


async def generate_response(
    llm: ChatOpenAI, question: str, contexts: list[str]
) -> str:
    """승인 사례 기반 응답 생성"""
    context_text = "\n\n---\n\n".join(
        f"[사례 {i + 1}]\n{ctx}" for i, ctx in enumerate(contexts)
    )
    prompt = f"""다음은 규제샌드박스 승인 사례 검색 결과입니다. 이 사례들을 참고하여 질문에 답변해주세요.

## 참고 승인 사례:
{context_text}

## 질문:
{question}

## 답변 지침:
- 검색된 승인 사례를 바탕으로 간결하고 정확하게 답변하세요.
- 사례의 서비스명, 트랙(실증특례/임시허가), 핵심 내용을 언급하세요.
- 검색된 사례에 없는 정보를 추측하지 마세요.
- 관련 사례가 여러 개이면 공통 패턴이나 특징을 정리해주세요."""

    response = await llm.ainvoke(prompt)
    return str(response.content)


# ---------------------------------------------------------------------------
# R2 고유 지표
# ---------------------------------------------------------------------------


@dataclass
class R2SpecificMetrics:
    must_include_coverage: float = 0.0
    must_include_matched: list[str] = field(default_factory=list)
    must_include_missed: list[str] = field(default_factory=list)
    must_not_include_violated: bool = False
    must_not_include_found: list[str] = field(default_factory=list)
    bullet_coverage: float | None = None
    bullet_details: list[dict] | None = None


def calculate_must_include_coverage(
    response: str, must_include: list[str]
) -> tuple[float, list[str], list[str]]:
    """must_include 키워드 커버리지 (대소문자 무시 문자열 포함 체크)"""
    if not must_include:
        return 1.0, [], []
    resp_lower = response.lower()
    matched = [kw for kw in must_include if kw.lower() in resp_lower]
    missed = [kw for kw in must_include if kw.lower() not in resp_lower]
    coverage = len(matched) / len(must_include)
    return coverage, matched, missed


def check_must_not_include(
    response: str, must_not_include: list[str]
) -> tuple[bool, list[str]]:
    """must_not_include 위반 여부"""
    if not must_not_include:
        return False, []
    resp_lower = response.lower()
    found = [kw for kw in must_not_include if kw.lower() in resp_lower]
    return len(found) > 0, found


BULLET_JUDGE_PROMPT = """당신은 답변 품질 평가자입니다. 아래 응답이 각 핵심 포인트를 다루고 있는지 판정하세요.

## 응답:
{response}

## 핵심 포인트:
{bullets_text}

## 판정 규칙:
- 각 포인트에 대해 응답이 해당 내용을 실질적으로 다루고 있으면 covered=true, 아니면 covered=false로 판정하세요.
- 정확한 표현 일치가 아니라 의미적 포함 여부를 판단하세요.
- 반드시 아래 JSON 배열만 출력하세요. 다른 텍스트는 출력하지 마세요.

## 출력 형식:
[
  {{"bullet": "포인트 텍스트", "covered": true, "reason": "판정 근거"}},
  ...
]"""


async def evaluate_bullet_coverage(
    judge_llm: ChatOpenAI,
    response: str,
    expected_bullets: list[str],
) -> tuple[float | None, list[dict] | None]:
    """expected_answer_bullets 커버리지를 LLM Judge로 평가"""
    if not expected_bullets:
        return None, None

    bullets_text = "\n".join(
        f"{i + 1}. {b}" for i, b in enumerate(expected_bullets)
    )
    prompt = BULLET_JUDGE_PROMPT.format(
        response=response, bullets_text=bullets_text
    )

    try:
        result = await judge_llm.ainvoke(prompt)
        content = str(result.content).strip()
        # JSON 배열 추출 (앞뒤 텍스트가 있을 수 있음)
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            details = json.loads(content[start:end])
        else:
            details = json.loads(content)

        covered_count = sum(1 for d in details if d.get("covered"))
        coverage = covered_count / len(expected_bullets)
        return coverage, details
    except Exception as e:
        print(f"    Bullet Judge 오류: {e}")
        return None, None


def aggregate_r2_specific_metrics(metrics_list: list[R2SpecificMetrics]) -> dict:
    if not metrics_list:
        return {}

    n = len(metrics_list)
    avg_mi = sum(m.must_include_coverage for m in metrics_list) / n
    total_kw = sum(
        len(m.must_include_matched) + len(m.must_include_missed) for m in metrics_list
    )
    total_matched = sum(len(m.must_include_matched) for m in metrics_list)
    violations = sum(1 for m in metrics_list if m.must_not_include_violated)

    bullet_scores = [
        m.bullet_coverage for m in metrics_list if m.bullet_coverage is not None
    ]
    avg_bullet = (
        sum(bullet_scores) / len(bullet_scores) if bullet_scores else None
    )
    total_bullets = sum(
        len(m.bullet_details) for m in metrics_list if m.bullet_details
    )
    total_covered = sum(
        sum(1 for b in m.bullet_details if b.get("covered"))
        for m in metrics_list
        if m.bullet_details
    )

    return {
        "avg_must_include_coverage": round(avg_mi, 4),
        "total_must_include_keywords": total_kw,
        "total_must_include_matched": total_matched,
        "must_not_include_violations": violations,
        "must_not_include_total_items": n,
        "violation_rate": round(violations / n, 4) if n > 0 else 0.0,
        "avg_bullet_coverage": round(avg_bullet, 4) if avg_bullet is not None else None,
        "total_bullets": total_bullets,
        "total_bullets_covered": total_covered,
    }


# ---------------------------------------------------------------------------
# Phase 1: 검색 (Retrieval) — 모델 무관, 1회만 실행
# ---------------------------------------------------------------------------


def retrieve_single_item(
    vectorstore,
    item: dict,
    top_k: int = 5,
) -> dict:
    """단일 항목 검색 (생성 모델 무관)

    Returns:
        검색 결과 딕셔너리 (contexts, retrieved_ids, metrics 등)
    """
    question = item["question"]
    gold_cases = item.get("gold_cases", [])
    negatives = item.get("negatives", [])

    gold_ids, must_have_ids = build_gold_case_ids(gold_cases)
    negative_ids = [n["case_id"] for n in negatives]

    start = time.perf_counter()
    results = vectorstore.similarity_search(question, k=top_k)
    latency = (time.perf_counter() - start) * 1000

    retrieved_ids = [extract_case_id_from_result(doc) for doc in results]
    contexts = [doc.content for doc in results]

    metrics, negative_at_k = calculate_r2_metrics(
        retrieved_ids, gold_ids, must_have_ids, negative_ids, top_k
    )

    return {
        "contexts": contexts,
        "retrieved_ids": retrieved_ids,
        "gold_ids": gold_ids,
        "must_have_ids": must_have_ids,
        "negative_ids": negative_ids,
        "retrieval_metrics": metrics,
        "negative_at_k": negative_at_k,
        "retrieval_latency_ms": round(latency, 2),
    }


# ---------------------------------------------------------------------------
# Phase 2: 생성 + 평가 (모델별 실행)
# ---------------------------------------------------------------------------


async def evaluate_generation_item(
    llm: ChatOpenAI,
    judge_llm: ChatOpenAI,
    evaluator: RAGASEvaluator,
    item: dict,
    retrieval_result: dict,
    bullet_judge_enabled: bool = True,
) -> tuple[LLMMetricsResult, R2SpecificMetrics, float, dict]:
    """단일 항목 생성 + 평가 (검색 결과 재사용)

    Returns:
        (llm_metrics, r2_metrics, generation_latency_ms, detail)
    """
    question = item["question"]
    contexts = retrieval_result["contexts"]
    ret_metrics: RetrievalMetrics = retrieval_result["retrieval_metrics"]

    # 생성
    gen_start = time.perf_counter()
    response = await generate_response(llm, question, contexts)
    gen_latency = (time.perf_counter() - gen_start) * 1000

    # R2 고유 지표
    mi_coverage, mi_matched, mi_missed = calculate_must_include_coverage(
        response, item.get("must_include", [])
    )
    mni_violated, mni_found = check_must_not_include(
        response, item.get("must_not_include", [])
    )

    # LLM Judge (비동기 병렬)
    ragas_task = evaluator.evaluate(question, response, contexts)

    if bullet_judge_enabled:
        bullet_task = evaluate_bullet_coverage(
            judge_llm, response, item.get("expected_answer_bullets", [])
        )
        llm_metrics, (bullet_cov, bullet_details) = await asyncio.gather(
            ragas_task, bullet_task
        )
    else:
        llm_metrics = await ragas_task
        bullet_cov, bullet_details = None, None

    r2_metrics = R2SpecificMetrics(
        must_include_coverage=mi_coverage,
        must_include_matched=mi_matched,
        must_include_missed=mi_missed,
        must_not_include_violated=mni_violated,
        must_not_include_found=mni_found,
        bullet_coverage=bullet_cov,
        bullet_details=bullet_details,
    )

    detail = {
        "id": item["id"],
        "category": item.get("category", ""),
        "query_type": item.get("query_type", ""),
        "question": question,
        "response": response,
        "contexts": contexts[:3],
        "gold_ids": retrieval_result["gold_ids"],
        "must_have_ids": retrieval_result["must_have_ids"],
        "negative_ids": retrieval_result["negative_ids"],
        "retrieved_ids": retrieval_result["retrieved_ids"][:5],
        # Retrieval (캐시에서 복사)
        "recall_at_k": ret_metrics.recall_at_k,
        "must_have_recall_at_k": ret_metrics.must_have_recall_at_k,
        "mrr": ret_metrics.mrr,
        "negative_at_k": retrieval_result["negative_at_k"],
        "retrieval_latency_ms": retrieval_result["retrieval_latency_ms"],
        # LLM
        "faithfulness": llm_metrics.faithfulness,
        "answer_relevancy": llm_metrics.answer_relevancy,
        "generation_latency_ms": round(gen_latency, 2),
        "llm_error": llm_metrics.error,
        # R2 고유
        "must_include_coverage": mi_coverage,
        "must_include_matched": mi_matched,
        "must_include_missed": mi_missed,
        "must_not_include_violated": mni_violated,
        "must_not_include_found": mni_found,
        "bullet_coverage": bullet_cov,
        "bullet_details": bullet_details,
    }

    return llm_metrics, r2_metrics, gen_latency, detail


# ---------------------------------------------------------------------------
# Phase 3: 모델 비교 테이블
# ---------------------------------------------------------------------------


def print_model_comparison(model_summaries: list[dict]):
    """모델 비교 테이블 출력"""
    if len(model_summaries) < 2:
        return

    col_width = 16
    table_width = 25 + col_width * len(model_summaries)

    print("\n" + "=" * table_width)
    print("생성 모델 비교")
    print("=" * table_width)

    header = f"{'지표':<25}"
    for ms in model_summaries:
        header += f"  {ms['model']:>{col_width - 2}}"
    print(header)
    print("─" * table_width)

    metrics_rows = [
        ("Faithfulness", "faithfulness", False),
        ("Answer Relevancy", "answer_relevancy", False),
        ("MI Coverage", "must_include_coverage", False),
        ("MNI Violation Rate", "must_not_include_violation_rate", True),
        ("Bullet Coverage", "bullet_coverage", False),
        ("Gen Latency P50", "generation_latency_p50_ms", True),
        ("Gen Latency P95", "generation_latency_p95_ms", True),
    ]

    for label, key, lower_is_better in metrics_rows:
        values = [ms["summary"].get(key) for ms in model_summaries]
        numeric = [v for v in values if v is not None]

        best_idx = None
        if len(numeric) > 1:
            best_val = min(numeric) if lower_is_better else max(numeric)
            for i, v in enumerate(values):
                if v == best_val:
                    best_idx = i
                    break

        row = f"{label:<25}"
        for i, v in enumerate(values):
            if v is None:
                formatted = "N/A"
            elif key.endswith("_ms"):
                formatted = f"{v:.0f}ms"
            else:
                formatted = f"{v:.4f}"
            marker = " *" if i == best_idx else "  "
            row += f"  {formatted + marker:>{col_width - 2}}"
        print(row)

    print("─" * table_width)
    print("  * = 해당 지표 최고 성능 (Violation Rate/Latency: 낮을수록 좋음)")


# ---------------------------------------------------------------------------
# 메인 평가 루프
# ---------------------------------------------------------------------------


async def run_evaluation_async(
    strategy: str = "structured",
    top_k: int = 5,
    output_name: str | None = None,
    limit: int | None = None,
    data_version: str = "enriched",
    embedding_config: EmbeddingConfig | None = None,
    models: list[str] | None = None,
    change_factor: str = "generation_model",
    change_value: str | None = None,
    tags: list[str] | None = None,
    description: str = "",
    bullet_judge_enabled: bool = True,
):
    """전체 평가 실행 (비동기)

    검색은 1회만 수행하고, 생성 모델별로 답변 생성 + 평가를 반복합니다.
    """
    if models is None:
        models = [DEFAULT_GENERATION_MODEL]

    print("=" * 70)
    print("R2 승인 사례 RAG 평가 (Retrieval + Generation + R2 Specific)")
    print("=" * 70)

    # 평가셋 로드
    eval_set = load_evaluation_set()
    items = eval_set.get("evaluation_items", [])
    if limit:
        items = items[:limit]
        print(f"\n  평가 항목 제한: {limit}개")

    # 데이터 로드
    case_data = load_case_data(data_version)
    emb_model_name = (
        embedding_config.model if embedding_config else settings.LLM_EMBEDDING_MODEL
    )

    print(f"\n평가셋: {len(items)}개 항목")
    print(f"Top-K: {top_k}")
    print(f"데이터: {data_version} ({len(case_data)}건)")
    print(f"전략: {strategy}")
    print(f"임베딩: {emb_model_name}")
    print(f"생성 모델: {', '.join(models)}")
    print(f"Judge: {JUDGE_MODEL}")
    print(f"Bullet Judge: {'ON' if bullet_judge_enabled else 'OFF'}")

    # Vector Store 생성 (1회)
    print("\nVector Store 생성 중...")
    build_start = time.perf_counter()
    vectorstore = create_temp_vector_store(
        case_data, strategy, embedding_config=embedding_config
    )
    build_time = (time.perf_counter() - build_start) * 1000
    print(f"Vector Store 준비 완료 ({build_time:.0f}ms)")

    # ── Phase 1: 검색 (모든 항목, 1회) ──────────────────────────────
    print(f"\n{'─' * 70}")
    print("[Phase 1] 검색 실행 (모델 무관, 1회)")
    print(f"{'─' * 70}\n")

    retrieval_cache: dict[str, dict] = {}
    all_retrieval_metrics: list[RetrievalMetrics] = []
    all_negatives: list[float] = []
    all_ret_latencies: list[float] = []

    for i, item in enumerate(items, 1):
        ret = retrieve_single_item(vectorstore, item, top_k)
        retrieval_cache[item["id"]] = ret
        all_retrieval_metrics.append(ret["retrieval_metrics"])
        all_negatives.append(ret["negative_at_k"])
        all_ret_latencies.append(ret["retrieval_latency_ms"])

        m = ret["retrieval_metrics"]
        neg_mark = " [NEG!]" if ret["negative_at_k"] > 0 else ""
        print(
            f"  [{i:2d}/{len(items)}] {item['id']} | "
            f"MH-R: {m.must_have_recall_at_k:.2f} | "
            f"R: {m.recall_at_k:.2f} | "
            f"MRR: {m.mrr:.2f} | "
            f"{ret['retrieval_latency_ms']:.0f}ms{neg_mark}"
        )

    ret_agg = aggregate_metrics(all_retrieval_metrics)
    avg_neg = sum(all_negatives) / len(all_negatives) if all_negatives else 0.0
    items_with_neg = sum(1 for n in all_negatives if n > 0)
    ret_p50 = statistics.median(all_ret_latencies)
    ret_p95 = (
        statistics.quantiles(all_ret_latencies, n=100)[94]
        if len(all_ret_latencies) >= 20
        else max(all_ret_latencies)
    )

    print(
        f"\n  Retrieval 요약: "
        f"MH-R={ret_agg['avg_must_have_recall_at_k']:.4f} | "
        f"R={ret_agg['avg_recall_at_k']:.4f} | "
        f"MRR={ret_agg['avg_mrr']:.4f} | "
        f"Neg={avg_neg:.4f} ({items_with_neg}건)"
    )

    # ── Phase 2: 생성 + 평가 (모델별) ──────────────────────────────
    judge_llm = get_llm(JUDGE_MODEL)
    evaluator = RAGASEvaluator(model=JUDGE_MODEL, api_key=settings.OPENAI_API_KEY)

    model_summaries: list[dict] = []
    saved_paths: list[Path] = []

    for model_name in models:
        print(f"\n{'─' * 70}")
        print(f"[Phase 2] 생성 모델: {model_name}")
        print(f"{'─' * 70}\n")

        llm = get_llm(model_name)

        all_llm_metrics: list[LLMMetricsResult] = []
        all_r2_metrics: list[R2SpecificMetrics] = []
        all_gen_latencies: list[float] = []
        all_details: list[dict] = []

        for i, item in enumerate(items, 1):
            ret_result = retrieval_cache[item["id"]]
            llm_metrics, r2_metrics, gen_lat, detail = (
                await evaluate_generation_item(
                    llm, judge_llm, evaluator, item, ret_result, bullet_judge_enabled
                )
            )

            all_llm_metrics.append(llm_metrics)
            all_r2_metrics.append(r2_metrics)
            all_gen_latencies.append(gen_lat)
            all_details.append(detail)

            # 진행 출력
            faith = (
                f"{llm_metrics.faithfulness:.2f}"
                if llm_metrics.faithfulness is not None
                else "N/A"
            )
            rel = (
                f"{llm_metrics.answer_relevancy:.2f}"
                if llm_metrics.answer_relevancy is not None
                else "N/A"
            )
            mi_total = len(r2_metrics.must_include_matched) + len(
                r2_metrics.must_include_missed
            )
            mi_str = f"{len(r2_metrics.must_include_matched)}/{mi_total}"
            mni_flag = " [MNI!]" if r2_metrics.must_not_include_violated else ""
            bullet_str = ""
            if r2_metrics.bullet_coverage is not None and r2_metrics.bullet_details:
                b_hit = sum(
                    1 for b in r2_metrics.bullet_details if b.get("covered")
                )
                bullet_str = (
                    f" | Bullet: {b_hit}/{len(r2_metrics.bullet_details)}"
                )

            print(
                f"  [{i:2d}/{len(items)}] {item['id']} | "
                f"Faith: {faith} | Rel: {rel} | "
                f"MI: {mi_str}{mni_flag}{bullet_str} | "
                f"Gen: {gen_lat:.0f}ms"
            )

        # 집계
        llm_agg = aggregate_llm_metrics(all_llm_metrics)
        r2_agg = aggregate_r2_specific_metrics(all_r2_metrics)

        gen_p50 = statistics.median(all_gen_latencies)
        gen_p95 = (
            statistics.quantiles(all_gen_latencies, n=100)[94]
            if len(all_gen_latencies) >= 20
            else max(all_gen_latencies)
        )

        # 모델 결과 요약 출력
        print(f"\n  --- {model_name} 결과 ---")
        f_val = llm_agg.get("avg_faithfulness")
        r_val = llm_agg.get("avg_answer_relevancy")
        print(
            f"  Faithfulness:         {f_val:.4f}"
            if f_val is not None
            else "  Faithfulness:         N/A"
        )
        print(
            f"  Answer Relevancy:     {r_val:.4f}"
            if r_val is not None
            else "  Answer Relevancy:     N/A"
        )
        print(
            f"  Must-Include Coverage: {r2_agg['avg_must_include_coverage']:.4f} "
            f"({r2_agg['total_must_include_matched']}/{r2_agg['total_must_include_keywords']})"
        )
        print(
            f"  MNI Violation Rate:    {r2_agg['violation_rate']:.1%} "
            f"({r2_agg['must_not_include_violations']}/{r2_agg['must_not_include_total_items']})"
        )
        if r2_agg.get("avg_bullet_coverage") is not None:
            print(
                f"  Bullet Coverage:       {r2_agg['avg_bullet_coverage']:.4f} "
                f"({r2_agg['total_bullets_covered']}/{r2_agg['total_bullets']})"
            )
        if llm_agg.get("errors", 0) > 0:
            print(f"  평가 오류:             {llm_agg['errors']}건")
        print(f"  Gen Latency P50:       {gen_p50:.0f}ms | P95: {gen_p95:.0f}ms")

        # summary 구성
        summary = {
            "must_have_recall_at_k": ret_agg["avg_must_have_recall_at_k"],
            "recall_at_k": ret_agg["avg_recall_at_k"],
            "mrr": ret_agg["avg_mrr"],
            "negative_at_k": round(avg_neg, 4),
            "items_with_negative": items_with_neg,
            "faithfulness": llm_agg.get("avg_faithfulness"),
            "answer_relevancy": llm_agg.get("avg_answer_relevancy"),
            "must_include_coverage": r2_agg["avg_must_include_coverage"],
            "must_not_include_violation_rate": r2_agg["violation_rate"],
            "bullet_coverage": r2_agg.get("avg_bullet_coverage"),
            "retrieval_latency_p50_ms": round(ret_p50, 2),
            "retrieval_latency_p95_ms": round(ret_p95, 2),
            "generation_latency_p50_ms": round(gen_p50, 2),
            "generation_latency_p95_ms": round(gen_p95, 2),
            "build_time_ms": round(build_time, 2),
        }

        model_summaries.append({"model": model_name, "summary": summary})

        # 결과 저장
        RESULTS_DIR_LLM.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")

        cv = model_name if len(models) > 1 else (change_value or model_name)
        experiment_id = f"{date_str}_{change_factor}_{cv}"

        result_data = {
            "experiment": {
                "id": experiment_id,
                "date": date_str,
                "timestamp": now.isoformat(timespec="seconds"),
                "description": description
                or f"R2 3단계: 생성 모델 비교 ({model_name})",
                "change_factor": change_factor,
                "change_value": cv,
                "tags": tags or [],
            },
            "config": {
                "strategy": strategy,
                "embedding_model": emb_model_name,
                "top_k": top_k,
                "num_cases": len(case_data),
                "num_eval_items": len(items),
                "data_version": data_version,
                "chunking": "none",
                "vector_db": "chroma_ephemeral",
                "generation_model": model_name,
                "judge_model": JUDGE_MODEL,
                "bullet_judge_enabled": bullet_judge_enabled,
            },
            "summary": summary,
            "retrieval_aggregated": ret_agg,
            "llm_aggregated": llm_agg,
            "r2_specific_aggregated": r2_agg,
            "details": all_details,
        }

        if output_name and len(models) == 1:
            filename = f"{output_name}.json"
        else:
            filename = f"{experiment_id}.json"

        result_path = RESULTS_DIR_LLM / filename
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        saved_paths.append(result_path)
        print(f"\n  결과 저장: {result_path}")

    # ── Phase 3: 비교 테이블 ────────────────────────────────────────
    if len(models) > 1:
        print_model_comparison(model_summaries)

    print(f"\n저장된 파일 ({len(saved_paths)}개):")
    for p in saved_paths:
        print(f"  {p}")

    # 임시 컬렉션 삭제
    try:
        vectorstore.delete_collection()
    except Exception:
        pass


def run_evaluation(**kwargs):
    """동기 래퍼"""
    asyncio.run(run_evaluation_async(**kwargs))


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="R2 승인 사례 RAG 평가 (Retrieval + Generation)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_GENERATION_MODEL,
        choices=[*GENERATION_MODELS, "all"],
        help=f"생성 모델 (기본: {DEFAULT_GENERATION_MODEL}, all=전체 비교)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="structured",
        choices=[*VALID_STRATEGIES],
        help="데이터 전략 (기본: structured)",
    )
    parser.add_argument(
        "--embedding",
        type=str,
        default=None,
        help="임베딩 프리셋 (E0/E1/E4/E5, eval/r2/configs/embedding.yaml)",
    )
    parser.add_argument("--top_k", type=int, default=5, help="Top-K (기본: 5)")
    parser.add_argument(
        "--output", type=str, default=None, help="결과 파일명 (단일 모델만)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="평가 항목 수 제한"
    )
    parser.add_argument(
        "--data-version",
        type=str,
        default="enriched",
        choices=["original", "enriched"],
        help="데이터 버전 (기본: enriched)",
    )
    parser.add_argument(
        "--change-factor", type=str, default="generation_model"
    )
    parser.add_argument("--change-value", type=str, default=None)
    parser.add_argument("--tags", type=str, default="", help="쉼표 구분 태그")
    parser.add_argument("--description", type=str, default="")
    parser.add_argument(
        "--trace", action="store_true", help="LangSmith 추적"
    )
    parser.add_argument(
        "--no-bullet-judge",
        action="store_true",
        help="Bullet Coverage LLM Judge 비활성화",
    )

    args = parser.parse_args()

    if args.trace:
        if enable_langsmith_tracing():
            print("LangSmith 추적 활성화됨")

    embedding_config = None
    if args.embedding:
        embedding_config = load_r2_embedding_config(args.embedding.upper())

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.model == "all":
        models = list(GENERATION_MODELS)
    else:
        models = [args.model]

    run_evaluation(
        strategy=args.strategy,
        top_k=args.top_k,
        output_name=args.output,
        limit=args.limit,
        data_version=args.data_version,
        embedding_config=embedding_config,
        models=models,
        change_factor=args.change_factor,
        change_value=args.change_value,
        tags=tags,
        description=args.description or "",
        bullet_judge_enabled=not args.no_bullet_judge,
    )


if __name__ == "__main__":
    main()
