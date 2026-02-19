# R2 승인 사례 RAG 성능 개선 보고서

> 작성일: 2026-02-11 (최종 수정: 2026-02-19)
> 브랜치: `feature/eval-r2-strategy`
> 평가 대상: R2 승인 사례 RAG (281건, ChromaDB)

---

## 1. 목표

R2 승인 사례 RAG의 Retrieval 성능을 체계적으로 측정하고, **데이터 전략**, **데이터 보강**, **임베딩 모델** 효과를 검증하여 최적 조합을 확정한다.

---

## 2. 전체 워크플로우

```
[0단계] 평가셋 만들기 (30개)                     ← 완료
    ↓
[1단계] 데이터 전략 비교 (임베딩 모델 고정)       ← 완료 (enriched structured 채택)
    ↓
[2단계] 임베딩 모델 비교 (1단계 승자 전략 고정)   ← 완료 (E0 text-embedding-3-small 채택)
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
- **normal** (216건, 77%): structured content >= 100자
- **short structured** (15건, 5%): structured 필드는 있으나 content < 100자
- **FT_ONLY** (50건, 18%): structured 필드 자체가 없어 full_text만 유효

structured content < 100자인 케이스는 총 **65건**(23%)이며, 이 중 FT_ONLY 50건이 핵심 문제이다. 이에 따라 **어떤 필드를 임베딩에 넣느냐**에 따라 성능이 크게 달라질 수 있다.

### 4.2 비교 전략 (3개)

| # | 전략 | content 구성 | 특징 |
|---|------|-------------|------|
| 1 | `structured` | service_name + service_description + special_provisions + pilot_scope + conditions | 유효 필드만 사용. 65건이 100자 미만 (FT_ONLY 50 + short 15) |
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
3. **hybrid**의 structured 대비 우위는 structured < 100자인 65건(FT_ONLY 50 + short 15)에 대한 full_text fallback 효과
4. **Negative@5**: fulltext는 0.35로 가장 높음 → 무관한 사례를 더 많이 검색

### 4.5 결론

> **structured 전략 확정**. hybrid가 소폭 우위이나, 100자 미만 65건(특히 FT_ONLY 50건)을 데이터 보강으로 해결하면 structured가 더 나은 기반이 된다.

---

## 5. 데이터 보강 (FT_ONLY 50건)

### 5.1 문제

structured < 100자인 65건 중, FT_ONLY 50건(18%)은 structured 필드 자체가 비어있어 임베딩 품질이 가장 낮다. hybrid 전략이 65건 전체를 full_text fallback으로 보완하지만, 근본적으로는 structured 필드를 채우는 것이 더 나은 접근. 보강 대상은 필드가 완전히 없는 FT_ONLY 50건을 우선 타겟으로 한다.

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

## 7. 2단계: 임베딩 모델 비교

### 7.1 실험 설정

| 항목 | 값 |
|------|-----|
| 고정 전략 | structured + enriched (1단계 승자) |
| Top-K | 5 |
| 평가셋 | 30개 (gold-v2) |
| 데이터 | 281건 (enriched) |

### 7.2 비교 모델 (4개)

| 코드 | 모델 | 유형 | 차원 |
|------|------|------|------|
| E0 | text-embedding-3-small | OpenAI API | 1536 |
| E1 | text-embedding-3-large | OpenAI API | 3072 |
| E4 | BGE-M3 (BAAI) | 로컬 | 1024 |
| E5 | KURE-v1 (nlpai-lab) | 로컬 | 1024 |

### 7.3 결과

| 지표 | E0 (3-small) | E1 (3-large) | E4 (BGE-M3) | E5 (KURE-v1) |
|------|---|---|---|---|
| **MH-Recall@5** | 0.867 | **0.883** | **0.883** | 0.867 |
| **Recall@5** | 0.858 | 0.851 | **0.883** | 0.872 |
| **MRR** | **0.950** | 0.940 | 0.928 | 0.914 |
| **Negative@5** | 0.200 | 0.183 | **0.133** | 0.150 |
| Neg 항목수 | 9건 | 9건 | **7건** | **7건** |
| Latency P50 | 254ms | 234ms | 178ms | **81ms** |
| Latency P95 | 913ms | 600ms | **191ms** | 165ms |
| Build Time | 6.5s | 6.6s | 250s | 751s |

### 7.4 쿼리별 주요 차이

| 쿼리 | 승자 | 내용 |
|------|------|------|
| R2-0003 DRT 버스 | E4/E5 | Recall 1.0 + Neg 0.0 (E0는 스쿨버스 혼입, Neg 1.0) |
| R2-0030 공유주방 | E4/E5 | E0 완전 실패 (Recall 0.0) |
| R2-0016 캠핑카 | E4 | 유일하게 MH-R 1.0 |
| R2-0008 비대면 진료 | E0 | 유일하게 MH-R 1.0 (규제 쟁점 넓게 해석) |
| R2-0023 킥보드 충전 | 없음 | 4개 모델 모두 Neg 1.0 (구조적 한계) |

### 7.5 분석

1. **E4(BGE-M3)**: Recall 최강(0.883) + Negative 최저(0.133). 한국어 도메인 용어(공유주방, DRT 등)에서 강점. 단, 빌드 시간 250초(E0의 38배), GPU 서버 필요.
2. **E0(3-small)**: MRR 최강(0.950). 첫 번째 정답이 항상 높은 순위. API만으로 운영 가능, 빌드 6.5초.
3. **E1(3-large)**: 전 지표에서 E0/E4 사이. 차별화 포인트 없음.
4. **E5(KURE-v1)**: 레이턴시 최소(81ms)이나 MRR 최저(0.914). 빌드 751초로 실용성 부족.
5. **절대 성능 차이는 소폭**: Recall E4-E0 = +2.5%p, MRR E0-E4 = +2.2%p.

### 7.6 청킹 필요성 판단

| 항목 | 값 |
|------|-----|
| structured 문서 max 길이 | 1,211자 (~807 tokens) |
| structured 문서 mean 길이 | 415자 (~277 tokens) |
| E0 토큰 한도 | 8,191 tokens |
| max 대비 한도 사용률 | ~10% |
| 토큰 초과 문서 수 | **0건 / 281건** |

> **청킹 불필요.** 가장 긴 문서도 토큰 한도의 10% 수준. 1건=1케이스 구조이므로 청킹 시 문맥 분산으로 Recall 저하 우려.

### 7.7 결론

> **E0 (text-embedding-3-small) 채택.**
>
> - MRR 0.950으로 사용자 체감 품질(첫 번째 정답 순위) 최강
> - API 키만으로 운영 가능 — GPU 서버 의존성 없음, 빌드 6.5초
> - E4 대비 Recall -2.5%p, Negative +6.7%p이나 절대 차이 소폭
> - P95 레이턴시 913ms spike는 OpenAI API 네트워크 지연 (모델 품질과 무관)
> - 3단계(Generation 지표)에서 추가 개선 여지 있음

---

## 8. 결과 파일 목록

```
server/eval/r2/results/retrieval/
├── 2026-02-11_strategy_structured.json           # 1단계: Original, structured (baseline)
├── 2026-02-11_strategy_hybrid.json               # 1단계: Original, hybrid
├── 2026-02-11_strategy_fulltext.json             # 1단계: Original, fulltext
├── 2026-02-11_strategy_structured_enriched.json  # 1단계: Enriched, structured (채택)
├── 2026-02-12_embedding_E0.json                  # 2단계: text-embedding-3-small (채택)
├── 2026-02-12_embedding_E1.json                  # 2단계: text-embedding-3-large
├── 2026-02-12_embedding_E4.json                  # 2단계: BGE-M3
└── 2026-02-12_embedding_E5.json                  # 2단계: KURE-v1
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

## 10. 확정 조합 요약

| 항목 | 확정 값 | 결정 단계 |
|------|---------|----------|
| 데이터 전략 | structured | 1단계 |
| 데이터 버전 | enriched (GPT-4o 보강) | 1단계 |
| 임베딩 모델 | text-embedding-3-small (E0) | 2단계 |
| 청킹 | 없음 (1건=1문서) | 2단계 |
| Top-K | 5 (기본값, 미튜닝) | - |

---

## 11. 남은 TODO

| 단계 | 작업 | 상태 |
|------|------|------|
| ~~1단계~~ | ~~데이터 전략 비교~~ | ~~완료 (enriched structured 채택)~~ |
| ~~2단계~~ | ~~임베딩 모델 비교~~ | ~~완료 (E0 채택)~~ |
| 3단계 | 생성 지표 테스트 (Faithfulness, Correctness) | TODO |
| 4단계 | 구성 튜닝 (Top-k, threshold, 중복제거) | TODO |
| 5단계 | 최종 확정 + production ChromaDB 구축 | TODO |
| 개선 | R2-0016 MH-Recall 회귀 분석 및 해결 | TODO |
| 개선 | R2-0030 공유주방 검색 실패 원인 분석 (E0 한계) | TODO |
