# R2 승인 사례 RAG 성능 개선 보고서

> 작성일: 2026-02-11
> 브랜치: `feature/eval-r2-strategy`
> 평가 대상: R2 승인 사례 RAG (281건, ChromaDB)

---

## 1. 목표

R2 승인 사례 RAG의 Retrieval 성능을 체계적으로 측정하고, **데이터 전략**과 **데이터 보강** 효과를 검증하여 최적 조합을 확정한다.

---

## 2. 전체 워크플로우

```
[0단계] 평가셋 만들기 (30개)                     ← 완료
    ↓
[1단계] 데이터 전략 비교 (임베딩 모델 고정)       ← 완료 (이 보고서)
    ↓
[2단계] 임베딩 모델 비교 (1단계 승자 전략 고정)   ← TODO
    ↓
[3단계] 생성 지표 테스트                         ← TODO
    ↓
[4단계] 구성 튜닝 (Top-k, threshold 등)          ← TODO
    ↓
[5단계] 최종 확정 및 안정 구간 기록               ← TODO
```

---

## 3. 평가 인프라

### 3.1 평가셋 (`evaluation_set.json`)

| 항목 | 값 |
|------|-----|
| 총 평가 항목 | 30개 |
| 도메인 | mobility(5), healthcare(5), fintech(5), platform(5), energy(4), logistics(3), etc(3) |
| 질문 유형 | similar_case(12), track_specific(6), condition_pattern(6), regulation_issue(6) |
| gold_cases 총수 | 96건 (must_have 47, 보조 49) |
| negatives 총수 | 38건 |

### 3.2 평가 지표

| 지표 | 설명 | 좋은 방향 |
|------|------|----------|
| **MH-Recall@K** | `must_have=true` 사례의 Top-K 검색률 | 높을수록 |
| **Recall@K** | 전체 gold_cases의 Top-K 검색률 | 높을수록 |
| **MRR** | 첫 번째 정답 사례의 역순위 (1/rank) | 높을수록 |
| **Negative@K** | Top-K 내 negative 사례 포함 비율 | 낮을수록 |

### 3.3 평가 환경

| 설정 | 값 |
|------|-----|
| Top-K | 5 |
| 임베딩 모델 | `text-embedding-3-small` (고정) |
| Vector DB | ChromaDB EphemeralClient (평가 전용) |
| 청킹 | 없음 (1건=1문서) |

### 3.4 실행 방법

```bash
# 전략별 평가 (3파일 생성)
cd server && uv run python eval/r2/run_evaluation.py --strategy all --tags gold-v2

# 보강 데이터 평가
cd server && uv run python eval/r2/run_evaluation.py \
  --data-version enriched --change-factor data --change-value enriched --tags gold-v2

# 결과 비교
cd server && uv run python eval/r2/compare_results.py --tag gold-v2
cd server && uv run python eval/r2/compare_results.py --tag gold-v2 --diff
```

---

## 4. 1단계: 데이터 전략 비교

### 4.1 배경

R2 데이터 281건 중 structured 필드 품질이 고르지 않다:
- **normal** (231건, 82%): structured content >= 100자
- **FT_ONLY** (50건, 18%): structured content < 100자, full_text만 유효

이에 따라 **어떤 필드를 임베딩에 넣느냐**에 따라 성능이 크게 달라질 수 있다.

### 4.2 비교 전략 (3개)

| # | 전략 | content 구성 | 특징 |
|---|------|-------------|------|
| 1 | `structured` | service_name + service_description + special_provisions + pilot_scope + conditions | 유효 필드만 사용. 50건이 100자 미만 |
| 2 | `hybrid` | structured 기반 + structured < 100자인 65건은 full_text로 대체 | 커버리지 100% |
| 3 | `fulltext` | 281건 모두 full_text만 사용 | structured 무시, 원문 전체 임베딩 |

### 4.3 결과

| 지표 | structured | hybrid | fulltext |
|------|-----------|--------|---------|
| **MH-Recall@5** | 0.861 | **0.889** | 0.672 |
| **Recall@5** | 0.786 | **0.830** | 0.597 |
| **MRR** | 0.911 | **0.917** | 0.717 |
| **Negative@5** | **0.20** | **0.20** | 0.35 |
| Neg Items | **9** | **9** | 14 |
| Latency P50 | 129ms | **122ms** | 129ms |

### 4.4 분석

1. **hybrid > structured > fulltext** 순서가 모든 핵심 지표에서 일관적
2. **fulltext**는 원문 전체를 임베딩하므로 노이즈가 많아 성능이 크게 하락
3. **hybrid**의 structured 대비 우위는 FT_ONLY 50건에 대한 full_text fallback 효과
4. **Negative@5**: fulltext는 0.35로 가장 높음 → 무관한 사례를 더 많이 검색

### 4.5 결론

> **structured 전략 확정**. hybrid가 소폭 우위이나, FT_ONLY 50건을 데이터 보강으로 해결하면 structured가 더 나은 기반이 된다.

---

## 5. 데이터 보강 (FT_ONLY 50건)

### 5.1 문제

FT_ONLY 50건(18%)은 structured 필드가 비어있어 structured 전략에서 임베딩 품질이 낮다. hybrid 전략이 이를 full_text fallback으로 보완하지만, 근본적으로는 structured 필드를 채우는 것이 더 나은 접근.

### 5.2 보강 방법

```bash
cd server && uv run python scripts/enrich_cases.py --apply --force
```

- **GPT-4o**로 full_text에서 structured 필드(service_name, service_description, special_provisions, pilot_scope, conditions) 추출
- 추출 결과: `server/eval/r2/enriched_50.json` (50건 검수용)
- 보강 적용 파일: `data/r2_data/cases_structured_enriched.json` (281건 전체)
- 원본 유지: `data/r2_data/cases_structured.json` (281건, 미보강)

### 5.3 보강 결과

- FT_ONLY: 50건(18%) → 3건(1%)
- 47건이 정상 structured content를 갖게 됨

### 5.4 gold_cases 전수 조사

데이터 보강으로 47건이 새롭게 검색 가능해지면서, 기존 gold_cases가 불완전해진다. 이에 50건 enriched 케이스 × 30개 쿼리를 클러스터링하여 전수 조사 실시.

**추가된 gold_cases: 20건 (6개 항목)**

| 항목 | 추가 건수 | 추가 사례 예시 |
|------|----------|---------------|
| R2-0008 | +1 | 임시허가_46_케이더봄 (비대면 진료) |
| R2-0010 | +2 | 실증특례_24_LG전자·서울대병원, 실증특례_23_LG전자·에임메드 |
| R2-0016 | +5 | 캠핑카 중개 클러스터 (어썸플랜, 지에스렌트카 등) |
| R2-0017 | +3 | 총회 전자의결 클러스터 (이보팅, 리빌드엑스, 이제이엠컴퍼니) |
| R2-0023 | +3 | PM 충전·주차 (포인테크 ID variant, LG전자, SKC) |
| R2-0028 | +6 | 스마트 보관 클러스터 (비즈하이브, 형동, 메타솔루션, 슈가맨, 에이블, 미니창고가방) |

---

## 6. 최종 결과: 보강 데이터 비교

### 6.1 4가지 실험 결과 (gold-v2 태그)

| 지표 | structured | hybrid | fulltext | **enriched** |
|------|-----------|--------|---------|-------------|
| **MH-Recall@5** | 0.861 | 0.889 | 0.672 | **0.872** |
| **Recall@5** | 0.786 | 0.830 | 0.597 | **0.858** |
| **MRR** | 0.911 | 0.917 | 0.717 | **0.950** |
| **Negative@5** | 0.20 | 0.20 | 0.35 | **0.20** |
| Neg Items | 9 | 9 | 14 | **9** |
| Latency P50 | 129ms | 122ms | 129ms | **109ms** |
| Build Time | 4084ms | 3718ms | 9913ms | **4059ms** |

> - `structured`, `hybrid`, `fulltext`: 원본 데이터(original) 사용
> - `enriched`: 보강 데이터 + structured 전략 사용

### 6.2 핵심 비교: Original structured vs Enriched structured

| 지표 | Original | Enriched | 변화 |
|------|----------|----------|------|
| MH-Recall@5 | 0.861 | **0.872** | +0.011 |
| Recall@5 | 0.786 | **0.858** | **+0.073** |
| MRR | 0.911 | **0.950** | **+0.039** |
| Negative@5 | 0.20 | 0.20 | 0 |

**항목별 주요 변화:**

| 항목 | 분류 | Original | Enriched | 원인 |
|------|------|----------|----------|------|
| R2-0010 | MH-R | 0.50 | **1.00** | 보강으로 LG전자·서울대병원 검색 가능 |
| R2-0023 | MH-R | 0.33 | **0.67** | 보강으로 포인테크 검색 개선 |
| R2-0008 | R | 0.67 | **1.00** | 케이더봄 검색 가능 |
| R2-0025 | R | 0.67 | **1.00** | 피알앤디 검색 개선 |
| R2-0017 | R | 0.43 | **0.71** | 총회 관련 Recall 개선 |
| R2-0016 | MH-R | **0.50** | 0.00 | must_have 2건(YONGHA, 진캠핑)이 밀림 (R은 0.44→0.56 개선) |

### 6.3 결론

> **Enriched structured 전략 채택.**
>
> - Recall@5 +7.3%, MRR +3.9% 대폭 개선
> - hybrid 대비 MH-Recall만 소폭 열위(0.872 vs 0.889), Recall(+0.028)과 MRR(+0.033)에서 우위
> - FT_ONLY 50건 보강으로 근본적 데이터 품질 향상 달성
> - R2-0016 MH-Recall 회귀(0.50→0.00)는 향후 개선 과제

---

## 7. 결과 파일

```
server/eval/r2/results/retrieval/
├── 2026-02-11_strategy_structured.json   # Original, structured (baseline)
├── 2026-02-11_strategy_hybrid.json       # Original, hybrid
├── 2026-02-11_strategy_fulltext.json     # Original, fulltext
└── 2026-02-11_strategy_structured_enriched.json         # Enriched, structured (채택)
```

모든 결과는 동일한 평가셋(gold-v2)으로 평가됨.

---

## 8. 파일 구조

```
server/
├── eval/
│   ├── metrics.py                        # 공통 Retrieval 지표
│   └── r2/
│       ├── README.md                     # 평가셋 설계 + 워크플로우 상세
│       ├── evaluation_set.json           # 평가셋 (30개, gold-v2)
│       ├── enriched_50.json              # FT_ONLY 50건 GPT-4o 추출 결과
│       ├── common.py                     # 공용 유틸 (VectorStore, 지표)
│       ├── run_evaluation.py             # Retrieval 평가 스크립트
│       ├── compare_results.py            # 결과 비교 스크립트
│       └── results/retrieval/            # 평가 결과 (4개 JSON)
├── scripts/
│   └── enrich_cases.py                   # FT_ONLY 보강 스크립트
└── data/r2_data/
    ├── cases_structured.json             # 원본 (281건, FT_ONLY 50건)
    └── cases_structured_enriched.json    # 보강본 (281건, FT_ONLY 3건)
```

---

## 9. 남은 TODO

| 단계 | 작업 | 상태 |
|------|------|------|
| 2단계 | 임베딩 모델 비교 (text-embedding-3-large, KURE-v1, BGE-M3) | TODO |
| 3단계 | 생성 지표 테스트 (Faithfulness, Correctness) | TODO |
| 4단계 | 구성 튜닝 (Top-k, threshold, 중복제거) | TODO |
| 5단계 | 최종 확정 + production ChromaDB 구축 | TODO |
| 개선 | R2-0016 MH-Recall 회귀 분석 및 해결 | TODO |
| 개선 | R2-0030 공유주방 검색 실패 원인 분석 | TODO |
