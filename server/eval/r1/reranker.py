"""BGE Cross-Encoder Reranker for R1 RAG

Bi-encoder vs Cross-encoder 비교:
- Bi-encoder: Query, Doc 각각 임베딩 → 코사인 유사도 (빠름, 정확도 낮음)
- Cross-encoder: Query+Doc 함께 입력 → 관련성 점수 (느림, 정확도 높음)

사용법:
    reranker = BGEReranker()
    reranked = reranker.rerank(query, documents, top_k=5)
"""

import time
from dataclasses import dataclass

from sentence_transformers import CrossEncoder


@dataclass
class RerankedResult:
    """Re-ranking 결과"""
    document: str
    original_rank: int
    new_rank: int
    score: float
    metadata: dict = None


class BGEReranker:
    """BGE Cross-Encoder 기반 Reranker

    모델: BAAI/bge-reranker-v2-m3
    - 다국어 지원 (한국어 포함)
    - 경량 모델 (CPU에서도 실행 가능)
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        """
        Args:
            model_name: Cross-encoder 모델명
                - BAAI/bge-reranker-v2-m3: 다국어, 경량
                - BAAI/bge-reranker-large: 영어 특화, 고성능
        """
        print(f"Loading Cross-Encoder model: {model_name}")
        self.model = CrossEncoder(model_name, max_length=512)
        self.model_name = model_name
        print("Model loaded successfully")

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
        return_scores: bool = True
    ) -> list[RerankedResult]:
        """문서 재정렬

        Args:
            query: 검색 쿼리
            documents: 후보 문서 리스트
            top_k: 반환할 상위 문서 수
            return_scores: 점수 포함 여부

        Returns:
            재정렬된 문서 리스트
        """
        if not documents:
            return []

        # Query-Document 쌍 생성
        pairs = [[query, doc] for doc in documents]

        # Cross-Encoder로 점수 계산
        start_time = time.time()
        scores = self.model.predict(pairs)
        latency_ms = (time.time() - start_time) * 1000

        # 점수 기준 정렬
        scored_docs = list(zip(documents, scores, range(len(documents))))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 결과 생성
        results = []
        for new_rank, (doc, score, original_rank) in enumerate(scored_docs[:top_k]):
            results.append(RerankedResult(
                document=doc,
                original_rank=original_rank,
                new_rank=new_rank,
                score=float(score)
            ))

        return results, latency_ms

    def rerank_with_ids(
        self,
        query: str,
        documents: list[str],
        doc_ids: list[str],
        top_k: int = 5
    ) -> tuple[list[str], list[str], float]:
        """ID와 함께 재정렬

        Args:
            query: 검색 쿼리
            documents: 후보 문서 내용 리스트
            doc_ids: 문서 ID 리스트
            top_k: 반환할 상위 문서 수

        Returns:
            (reranked_docs, reranked_ids, latency_ms)
        """
        if not documents:
            return [], [], 0.0

        # Query-Document 쌍 생성
        pairs = [[query, doc] for doc in documents]

        # Cross-Encoder로 점수 계산
        start_time = time.time()
        scores = self.model.predict(pairs)
        latency_ms = (time.time() - start_time) * 1000

        # 점수 기준 정렬
        scored = list(zip(documents, doc_ids, scores))
        scored.sort(key=lambda x: x[2], reverse=True)

        # Top-K 추출
        reranked_docs = [item[0] for item in scored[:top_k]]
        reranked_ids = [item[1] for item in scored[:top_k]]

        return reranked_docs, reranked_ids, latency_ms


# 테스트용
if __name__ == "__main__":
    print("=== BGE Reranker 테스트 ===\n")

    reranker = BGEReranker()

    query = "신속확인 처리 기한이 어떻게 되나요?"

    documents = [
        "규제샌드박스는 신기술 제품과 서비스를 시험할 수 있는 제도입니다.",
        "신속확인의 처리 기한은 30일 이내입니다.",
        "임시허가는 안전성이 검증된 서비스에 부여됩니다.",
        "실증특례 유효기간은 2년입니다.",
        "신속확인 제도는 규제 유무를 확인하는 절차입니다.",
    ]

    print(f"Query: {query}\n")
    print("Original order:")
    for i, doc in enumerate(documents):
        print(f"  {i}: {doc[:50]}...")

    results, latency = reranker.rerank(query, documents)

    print(f"\nReranked (latency: {latency:.1f}ms):")
    for r in results:
        print(f"  {r.new_rank}: [was {r.original_rank}] score={r.score:.3f} | {r.document[:40]}...")
