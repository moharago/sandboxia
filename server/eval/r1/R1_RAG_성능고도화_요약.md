# R1 RAG 성능 고도화 요약

> 규제제도 & 절차 RAG 검색 성능 개선 실험 결과

## 평가 개요

| 항목 | 값 |
|------|-----|
| 평가 기간 | 2026-02-25 ~ 02-26 |
| 평가셋 | 30개 질의-정답 쌍 |
| 검색 대상 | 147개 청크 (평균 763자) |

---

## 1. 임베딩 모델 비교

| 모델 | Provider | Dimension | Must-Have Recall@5 | MRR | Latency |
|------|----------|-----------|-------------------|-----|---------|
| E0: text-embedding-3-small | OpenAI | 1536 | 66.67% | 72.22% | 197ms |
| **E1: text-embedding-3-large** | OpenAI | 3072 | **73.33%** | **88.33%** | **151ms** |
| E2: solar-embedding-1-large | Upstage | 4096 | 71.67% | 74.83% | 603ms |

### 최종 선택: E1 (text-embedding-3-large)

**선정 이유:**
- 최고 성능 (MRR 88.33%)
- 최저 지연시간 (E2 대비 4배 빠름)
- 규제 전문 용어 처리에 우수

---

## 2. 검색 전략 비교

### Hybrid Search (Vector + BM25)

| 전략 | Must-Have Recall@5 | MRR |
|------|-------------------|-----|
| **Vector Search (100%)** | **73.33%** | **88.33%** |
| Hybrid (50/50) | 65.00% | 66.67% |
| Hybrid (80/20) | 68.33% | 78.33% |

**결론:** Hybrid Search 미적용 (성능 저하 -8.33%p)

### Query Rewriting

| 전략 | Must-Have Recall@5 | MRR |
|------|-------------------|-----|
| **Vector Search** | **73.33%** | **88.33%** |
| + Query Rewriting | 73.33% | 85.83% |

**결론:** 미적용 (효과 미미 + LLM 호출 비용)

### Reranking (bge-reranker-v2-m3)

| 전략 | Must-Have Recall@5 | Latency |
|------|-------------------|---------|
| Vector Search | 73.33% | 151ms |
| + Reranking | **90.00%** | **19,555ms** |

**결론:** 실시간 서비스 부적합 (129배 지연), 배치 처리만 검토

---

## 3. 성능 개선 결과

### Baseline → Production

| 지표 | Baseline (E0) | Production (E1) | 개선률 |
|------|--------------|-----------------|--------|
| Must-Have Recall@5 | 66.67% | 73.33% | **+10.0%** |
| Recall@5 | 58.33% | 68.61% | **+17.6%** |
| MRR | 72.22% | 88.33% | **+22.3%** |
| Latency | 197ms | 151ms | **-23.4%** |
| Latency P95 | 512ms | 279ms | **-45.3%** |

---

## 4. 최종 Production 설정

```yaml
embedding:
  model: text-embedding-3-large
  provider: openai
  dimension: 3072

retrieval:
  search_type: vector  # pure vector search
  top_k: 5

# 미적용:
# - Hybrid Search: 성능 저하
# - Query Rewriting: 효과 미미
# - Reranking: 실시간성 불가
```

---

## 5. 벡터DB

| 항목 | 현재 | 향후 검토 |
|------|------|----------|
| DB | ChromaDB | Qdrant |
| 검색 | Vector Search | Sparse-Dense Hybrid |
| 용도 | 개발/테스트 | 프로덕션 확장 |

---

## 6. 추가 개선 가능성

### Track Prefix 적용 시 (LLM 평가)

| 설정 | Must-Have Recall@5 | Faithfulness |
|------|-------------------|--------------|
| 기본 | 73.33% | 98.67% |
| **Track Prefix** | **88.33%** | 97.85% |

청크에 `[신속확인]`, `[실증특례]` 등 트랙 prefix 추가 시 **+15%p** 추가 개선 가능

---

## 핵심 요약

```
임베딩: text-embedding-3-small → text-embedding-3-large
검색:   Vector Search (Hybrid/Reranking 미적용)
성능:   MRR 72% → 88% (+22%), Latency 197ms → 151ms (-23%)
```
