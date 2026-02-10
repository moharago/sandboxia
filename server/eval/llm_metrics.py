"""LLM-as-Judge 방식의 RAG 평가 지표 모듈 (RAGAS 기반)

LLM을 평가자로 사용하여 Generation 품질을 측정합니다.

지표:
- Faithfulness: 응답이 컨텍스트에 기반하는지 (환각 방지)
- Answer Relevancy: 응답이 질문에 적절히 답변하는지
- Factual Correctness: 응답이 예상 답변과 사실적으로 일치하는지 (Reference 필요)
"""

import asyncio
import concurrent.futures
from dataclasses import dataclass

from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics import Faithfulness, ResponseRelevancy


@dataclass
class LLMMetricsResult:
    """LLM-as-Judge 평가 결과"""

    faithfulness: float | None
    answer_relevancy: float | None
    error: str | None = None


class RAGASEvaluator:
    """RAGAS 기반 LLM-as-Judge 평가기

    Usage:
        evaluator = RAGASEvaluator(model="gpt-4.1")

        result = await evaluator.evaluate(
            question="간편결제 서비스에서 부정결제 사고가 발생하면 책임은 누가 지나요?",
            response="원칙적으로 금융회사가 책임을 부담합니다.",
            contexts=["전자금융거래법 제9조 ① 금융회사는..."]
        )

        print(f"Faithfulness: {result.faithfulness}")
        print(f"Answer Relevancy: {result.answer_relevancy}")
    """

    def __init__(
        self,
        model: str = "gpt-4.1",
        embedding_model: str = "text-embedding-3-small",
        api_key: str | None = None,
    ):
        """RAGAS 평가기 초기화

        Args:
            model: 평가에 사용할 LLM 모델 (기본: gpt-4.1)
            embedding_model: 임베딩 모델 (기본: text-embedding-3-small)
            api_key: OpenAI API 키 (없으면 환경변수 사용)
        """
        self.model = model

        # OpenAI 비동기 클라이언트 생성
        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        self.async_client = AsyncOpenAI(**client_kwargs)

        # RAGAS LLM 및 Embeddings 초기화 (비동기 클라이언트 사용)
        self.llm = llm_factory(model=model, client=self.async_client)
        self.embeddings = embedding_factory(provider="openai", model=embedding_model, client=self.async_client)

        # 메트릭 초기화
        self.faithfulness_scorer = Faithfulness(llm=self.llm)
        self.relevancy_scorer = ResponseRelevancy(llm=self.llm, embeddings=self.embeddings)

    async def evaluate_faithfulness(
        self,
        question: str,
        response: str,
        contexts: list[str],
    ) -> float | None:
        """Faithfulness 평가

        응답의 모든 주장이 컨텍스트에서 추론 가능한지 확인합니다.

        Args:
            question: 사용자 질문
            response: LLM 응답
            contexts: 검색된 컨텍스트 목록

        Returns:
            0.0 ~ 1.0 사이의 점수 (1.0이 가장 좋음)
        """
        try:
            result = await self.faithfulness_scorer.ascore(
                user_input=question,
                response=response,
                retrieved_contexts=contexts,
            )
            return result.value
        except Exception as e:
            print(f"Faithfulness 평가 오류: {e}")
            return None

    async def evaluate_answer_relevancy(
        self,
        question: str,
        response: str,
    ) -> float | None:
        """Answer Relevancy 평가

        응답이 질문에 적절히 답변하는지 확인합니다.

        Args:
            question: 사용자 질문
            response: LLM 응답

        Returns:
            0.0 ~ 1.0 사이의 점수 (1.0이 가장 좋음)
        """
        try:
            result = await self.relevancy_scorer.ascore(
                user_input=question,
                response=response,
            )
            return result.value
        except Exception as e:
            print(f"Answer Relevancy 평가 오류: {e}")
            return None

    async def evaluate(
        self,
        question: str,
        response: str,
        contexts: list[str],
    ) -> LLMMetricsResult:
        """전체 LLM-as-Judge 지표 평가

        Args:
            question: 사용자 질문
            response: LLM 응답
            contexts: 검색된 컨텍스트 목록

        Returns:
            LLMMetricsResult 객체
        """
        try:
            # 병렬로 평가 실행
            faithfulness_task = self.evaluate_faithfulness(question, response, contexts)
            relevancy_task = self.evaluate_answer_relevancy(question, response)

            faithfulness, relevancy = await asyncio.gather(
                faithfulness_task,
                relevancy_task,
            )

            return LLMMetricsResult(
                faithfulness=faithfulness,
                answer_relevancy=relevancy,
            )
        except Exception as e:
            return LLMMetricsResult(
                faithfulness=None,
                answer_relevancy=None,
                error=str(e),
            )

    def evaluate_sync(
        self,
        question: str,
        response: str,
        contexts: list[str],
    ) -> LLMMetricsResult:
        """동기 방식 평가 (기존 이벤트 루프 내에서도 호출 가능)

        FastAPI 핸들러 등 이미 이벤트 루프가 실행 중인 환경에서도
        안전하게 호출할 수 있습니다. 이벤트 루프가 없으면 새로 생성합니다.
        """
        coro = self.evaluate(question, response, contexts)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 이벤트 루프가 없는 경우 새로 생성하여 실행
            return asyncio.run(coro)

        # 이벤트 루프가 실행 중인 경우 별도 스레드에서 실행
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


def aggregate_llm_metrics(results: list[LLMMetricsResult]) -> dict:
    """여러 평가 항목의 LLM 지표를 집계

    Args:
        results: LLMMetricsResult 목록

    Returns:
        집계된 평균 지표
    """
    if not results:
        return {}

    faithfulness_scores = [r.faithfulness for r in results if r.faithfulness is not None]
    relevancy_scores = [r.answer_relevancy for r in results if r.answer_relevancy is not None]

    return {
        "num_evaluated": len(results),
        "avg_faithfulness": (
            round(sum(faithfulness_scores) / len(faithfulness_scores), 4) if faithfulness_scores else None
        ),
        "avg_answer_relevancy": (round(sum(relevancy_scores) / len(relevancy_scores), 4) if relevancy_scores else None),
        "faithfulness_evaluated": len(faithfulness_scores),
        "relevancy_evaluated": len(relevancy_scores),
        "errors": sum(1 for r in results if r.error is not None),
    }
