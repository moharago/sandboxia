# R1 RAG 성능 고도화 리포트

## 개요

규제제도 & 절차 RAG (R1)의 검색 성능을 향상시키기 위해 다양한 실험을 수행했습니다.
평가셋은 30개의 질의-정답 쌍으로 구성되어 있으며, 147개 청크에서 검색을 수행합니다.

**평가 지표:**
- **Must-Have Recall@K**: 반드시 포함되어야 하는 핵심 문서의 검색률
- **Recall@K**: 전체 관련 문서의 검색률
- **MRR (Mean Reciprocal Rank)**: 첫 번째 정답 문서의 순위 (높을수록 상위 노출)
- **Latency**: 검색 응답 시간 (ms)

---

## 1. 임베딩 모델 비교

### 실험 설정
- Search Type: Vector Search
- Top-K: 5
- 평가일: 2026-02-25

### 결과

| Config | 모델 | Provider | Must-Have Recall@K | Recall@K | MRR | Latency (ms) |
|--------|------|----------|-------------------|----------|-----|--------------|
| **E0** (Baseline) | text-embedding-3-small | OpenAI | 66.67% | 58.33% | 72.22% | 197.54 |
| **E1** | text-embedding-3-large | OpenAI | **73.33%** | **68.61%** | **88.33%** | **151.53** |
| **E2** | solar-embedding-1-large | Upstage | 71.67% | 61.94% | 74.83% | 603.89 |

### 분석

**E1 (text-embedding-3-large) 선정 이유:**

1. **최고 성능**: Must-Have Recall 73.33%, MRR 88.33%로 모든 지표에서 최고
2. **최저 지연시간**: 151ms로 가장 빠름 (E0 대비 23% 개선)
3. **비용 효율**: 유료 API지만 성능 대비 합리적

**E0 → E1 개선 효과:**
- Must-Have Recall: +6.66%p (66.67% → 73.33%)
- MRR: +16.11%p (72.22% → 88.33%)
- Latency: -23% (197ms → 151ms)

**E2 (Upstage Solar) 분석:**
- 한국어 특화 모델이지만 MRR에서 E1보다 낮음
- 지연시간이 4배 이상 높음 (603ms)
- 규제 문서 도메인에서는 OpenAI large 모델이 더 효과적

---

## 2. 검색 전략 비교

### 실험 설정
- Embedding: E1 (text-embedding-3-large)
- Top-K: 5 (별도 명시 없는 경우)

### 결과

| 전략 | Must-Have Recall@K | Recall@K | MRR | Latency (ms) |
|------|-------------------|----------|-----|--------------|
| **Vector Search** (기준) | 73.33% | 68.61% | 88.33% | 151.53 |
| Hybrid (50% vector) | 65.00% | 56.94% | 66.67% | 187.85 |
| Hybrid (80% vector) | 68.33% | 59.72% | 78.33% | 192.84 |
| Query Rewriting | 73.33% | 66.67% | 85.83% | - |
| Top-K=10 | 73.33% | 67.78% | 83.89% | 179.53 |
| **+ Reranking** | **90.00%** | **76.39%** | **91.11%** | 19,555 |

### 분석

**Hybrid Search (Vector + BM25):**
- 예상과 달리 순수 Vector Search보다 성능 저하
- 규제 문서 특성상 키워드 매칭보다 의미적 유사도가 더 중요
- **결론: Hybrid Search 미적용**

**Query Rewriting:**
- LLM으로 질의를 검색에 최적화된 형태로 변환
- 성능 향상 미미 (MRR 오히려 감소)
- 추가 LLM 호출로 인한 지연시간 증가
- **결론: Query Rewriting 미적용**

**Top-K 확장 (5 → 10):**
- Recall 변화 없음, MRR 약간 감소
- 더 많은 문서 반환해도 정답 검색률 동일
- **결론: Top-K=5 유지**

**Reranking (BAAI/bge-reranker-v2-m3):**
- Must-Have Recall: +16.67%p (73.33% → 90.00%)
- MRR: +2.78%p (88.33% → 91.11%)
- **단점**: 지연시간 100배 증가 (151ms → 19,555ms)
- **결론: 실시간 서비스에는 부적합, 배치 처리용으로 고려**

---

## 3. 최종 권장 설정

### Production 설정

```yaml
embedding:
  model: text-embedding-3-large
  provider: openai

retrieval:
  search_type: vector  # pure vector search
  top_k: 5

# Hybrid search: 미적용 (성능 저하)
# Query rewriting: 미적용 (효과 미미)
# Reranking: 미적용 (지연시간 과다)
```

### 성능 요약

| 지표 | Baseline (E0) | Production (E1) | 개선률 |
|------|---------------|-----------------|--------|
| Must-Have Recall@5 | 66.67% | 73.33% | **+10.0%** |
| MRR | 72.22% | 88.33% | **+22.3%** |
| Latency | 197ms | 151ms | **-23.4%** |

---

## 4. 향후 개선 방향

### 단기

1. **청킹 전략 최적화**
   - 현재 평균 청크 길이: 763.6자
   - 문서 구조 기반 청킹으로 의미 단위 보존

2. **메타데이터 필터링**
   - 트랙별 (신속확인/실증특례/임시허가) 필터 적용
   - 카테고리별 가중치 부여

### 중기

3. **Qdrant 전환 검토**
   - ChromaDB → Qdrant 마이그레이션
   - Sparse-Dense Hybrid Search 지원
   - 프로덕션 레벨 확장성

4. **한국어 특화 임베딩 재평가**
   - KURE-v1 (nlpai-lab): 한국어 이해 특화
   - BGE-M3-Korean: 다국어 + 한국어 최적화
   - 도메인 특화 파인튜닝 검토

### 장기

5. **비동기 Reranking**
   - 초기 응답: Vector Search (150ms)
   - 백그라운드 Rerank 후 결과 갱신
   - 점진적 UX 개선

---

## 부록: 평가 결과 파일 위치

```
server/eval/r1/results/retrieval/
├── 2026-02-25_embedding_E0.json     # Baseline
├── 2026-02-25_embedding_E1.json     # text-embedding-3-large
├── 2026-02-25_embedding_E2.json     # Upstage Solar
├── 2026-02-25_hybrid_0.5.json       # Hybrid 50%
├── 2026-02-25_hybrid_0.8.json       # Hybrid 80%
├── 2026-02-25_query_rewriting.json  # Query Rewriting
├── 2026-02-25_topk_10.json          # Top-K=10
└── 2026-02-26_rerank_test.json      # Reranking
```

---

*Generated: 2026-02-27*
