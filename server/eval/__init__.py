"""RAG 평가 모듈

Retrieval 지표:
- Recall@K: Top-K 안에 gold 청크 포함 비율
- Must-Have Recall@K: must_have=true인 핵심 청크 검색률
- MRR (Mean Reciprocal Rank): 첫 번째 정답의 역순위 평균

LLM-as-Judge 지표 (RAGAS 기반):
- Faithfulness: 응답이 컨텍스트에 기반하는지 (환각 방지)
- Response Relevancy: 응답이 질문에 적절히 답변하는지
"""

from eval.llm_metrics import (
    LLMMetricsResult,
    RAGASEvaluator,
    aggregate_llm_metrics,
)
from eval.metrics import (
    RetrievalMetrics,
    aggregate_metrics,
    calculate_mrr,
    calculate_recall_at_k,
    calculate_retrieval_metrics,
)

__all__ = [
    # Retrieval 지표
    "RetrievalMetrics",
    "calculate_recall_at_k",
    "calculate_mrr",
    "calculate_retrieval_metrics",
    "aggregate_metrics",
    # LLM-as-Judge 지표
    "LLMMetricsResult",
    "RAGASEvaluator",
    "aggregate_llm_metrics",
]
