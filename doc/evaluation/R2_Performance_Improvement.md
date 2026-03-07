# R2 승인 사례 RAG 성능 개선 보고서

> 작성일: 2026-02-11 (최종 수정: 2026-03-06)
> 브랜치: `feature/eval-r2-strategy`, `eval/rag-r2`
> 평가 대상: R2 승인 사례 RAG (281건)

---

## 1. 목표

R2 승인 사례 RAG의 Retrieval + Generation 성능을 체계적으로 측정하고, **데이터 전략**, **데이터 보강**, **임베딩 모델**, **생성 모델**, **구성 튜닝**의 효과를 검증하여 최적 조합을 확정한다.

---

## 2. 데이터 출처: PDF 파싱과 그 한계

### 2.1 원본 데이터 수집

R2 RAG의 원본 데이터는 **규제 샌드박스 승인 사례 PDF 문서 281건**이다. 규제 샌드박스 운영 기관(과기부, 산업부, 금융위 등)이 공개한 승인/반려 사례 문서를 수집하여 PDF에서 텍스트를 추출하고, 정형 필드로 파싱한 결과가 `cases_structured.json`이다.

### 2.2 PDF 파싱의 구조적 한계

PDF 파싱 과정에서 다음과 같은 품질 문제가 발생했다:

| 문제 | 상세 | 영향 |
|------|------|------|
| **양식 비표준** | PDF마다 양식이 다르고, 일부는 스캔 이미지(OCR 필요) | 정규식 패턴 매칭 실패, 필드 추출 누락 |
| **필드 빈값 과다** | `service_description` 49.8% 빈값, `current_regulation` 98.9% 빈값 | 임베딩 벡터가 핵심 정보를 담지 못함 |
| **FT_ONLY 케이스** | 281건 중 50건(18%)은 structured 필드 자체가 비어있음 | 서비스명/설명 없이 원문 텍스트만 존재 |
| **OCR 깨짐** | 일부 사례에서 한글 깨짐, 표 구조 손실 | 키워드 매칭 실패, 노이즈 유입 |

### 2.3 데이터 품질 분류

파싱 품질에 따라 281건을 세 그룹으로 분류:

| 그룹 | 기준 | 건수 (비율) | 특성 |
|------|------|------------|------|
| **normal** | structured content >= 100자 | 216건 (77%) | 서비스명, 설명, 특례범위 등 핵심 필드 존재 |
| **short structured** | structured 필드 있으나 < 100자 | 15건 (5%) | 필드는 있지만 내용이 너무 짧음 |
| **FT_ONLY** | structured 필드 자체가 없음 | 50건 (18%) | `full_text`(PDF 원문 전체)만 유효 |

> `full_text`는 281건 모두 존재(0% 빈값). 하지만 PDF 원문에는 머리글, 서식, 표 잔해 등 노이즈가 포함되어 있어 그대로 임베딩하면 검색 정밀도가 떨어진다.

### 2.4 왜 이것이 RAG 성능에 직결되는가

임베딩 기반 검색은 **"문서 벡터와 쿼리 벡터의 유사도"**로 동작한다. structured 필드가 비어있으면 해당 사례의 벡터에 핵심 정보(서비스명, 기술, 규제 쟁점)가 담기지 않아, 아무리 관련 있는 쿼리가 들어와도 검색 결과에 나타나지 않는다. 이것이 "어떤 필드를 임베딩에 넣느냐"가 R2 성능의 첫 번째 변수가 된 이유이다.

---

## 3. 전체 워크플로우

```
[0단계] 평가셋 만들기 (30개)                     ← 완료
    ↓
[1단계] 데이터 전략 비교 (임베딩 모델 고정)       ← 완료 (structured 채택)
    ↓
[1.5단계] 데이터 보강 (FT_ONLY 50건 GPT-4o)     ← 완료 (enriched structured 채택)
    ↓
[2단계] 임베딩 모델 비교 (1단계 승자 전략 고정)   ← 완료 (E0 text-embedding-3-small 채택)
    ↓
[3단계] 생성 모델 비교 (RAGAS 4개 모델)          ← 완료 (gpt-4o 채택)
    ↓
[4단계] 구성 튜닝 (Top-k, threshold)             ← 완료 (top_k=5, threshold 없음)
    ↓
[5단계] 최종 확정 및 안정 구간 기록               ← 완료
```

**핵심 원칙**: "한 번에 하나의 변수만 변경". 각 단계에서 이전 단계의 확정 값을 고정하고 하나의 변수만 바꿔서 비교한다. 이를 통해 각 선택의 효과를 정확히 분리하고, 모든 실험을 재현 가능하게 만든다.

---

## 4. 평가 인프라

### 4.1 평가셋 (`evaluation_set.json`)

| 항목 | 값 |
|------|-----|
| 총 평가 항목 | 30개 |
| 도메인 | mobility(5), healthcare(5), fintech(5), platform(5), energy(4), logistics(3), etc(3) |
| 질문 유형 | similar_case(12), track_specific(6), condition_pattern(6), regulation_issue(6) |
| gold_cases 총수 | 96건 (must_have 47, 보조 49) |
| negatives 총수 | 38건 |

질문은 실제 컨설턴트가 물어볼 법한 현업 표현을 사용했다:
- "자율주행 배달 로봇 서비스를 시작하려는데 비슷한 승인 사례가 있나요?"
- "원격으로 환자 모니터링하는 서비스가 실증특례 받은 적 있나요?"

### 4.2 Retrieval 평가 지표

| 지표 | 설명 | 좋은 방향 |
|------|------|----------|
| **MH-Recall@K** | `must_have=true` 사례의 Top-K 검색률 | 높을수록 |
| **Recall@K** | 전체 gold_cases의 Top-K 검색률 | 높을수록 |
| **MRR** | 첫 번째 정답 사례의 역순위 (1/rank) | 높을수록 |
| **Negative@K** | Top-K 내 negative 사례 포함 비율 | 낮을수록 |

### 4.3 Generation 평가 지표

| 지표 | 설명 | 평가 방식 |
|------|------|----------|
| **Faithfulness** | 응답이 컨텍스트에 기반하는지 (환각 방지) | RAGAS (gpt-4.1 Judge) |
| **Answer Relevancy** | 응답이 질문에 적절히 답변하는지 | RAGAS (gpt-4.1 Judge) |
| **Must-Include Coverage** | `must_include` 키워드 포함 비율 | 문자열 매칭 |
| **Must-Not-Include Violation** | `must_not_include` 키워드 위반 여부 | 문자열 매칭 |
| **Bullet Coverage** | `expected_answer_bullets` 핵심 포인트 커버 비율 | LLM Judge (gpt-4.1) |

### 4.4 평가 환경

| 설정 | 값 |
|------|-----|
| Top-K | 5 (기본값, 4단계에서 튜닝) |
| Vector DB | ChromaDB EphemeralClient (평가 전용, 운영 DB 오염 방지) |
| 청킹 | 없음 (1건=1문서) |

### 4.5 실행 방법

```bash
# Retrieval 평가
cd server && uv run python eval/r2/run_evaluation.py --strategy all --tags gold-v2

# 보강 데이터 Retrieval 평가
cd server && uv run python eval/r2/run_evaluation.py \
  --data-version enriched --change-factor data --change-value enriched --tags gold-v2

# 임베딩 모델 비교
cd server && uv run python eval/r2/run_evaluation.py \
  --data-version enriched --embedding all --tags stage2

# LLM 생성 모델 비교
cd server && uv run python eval/r2/run_llm_evaluation.py --model all --tags stage3

# 구성 튜닝 (top_k)
cd server && uv run python eval/r2/run_evaluation.py \
  --data-version enriched --embedding E0 --top-k 3 --tags stage4

# 구성 튜닝 (threshold)
cd server && uv run python eval/r2/run_evaluation.py \
  --data-version enriched --embedding E0 --threshold 0.3 --tags stage4

# 결과 비교
cd server && uv run python eval/r2/compare_results.py --tag stage2
cd server && uv run python eval/r2/compare_results.py --llm --tag stage3
```

---

## 5. 0단계: 평가셋 만들기

### 5.1 왜 평가셋이 필요한가

성능 개선은 **"측정 → 변경 → 재측정 → 비교"** 사이클로 진행된다. "이 모델이 더 나은 것 같다"는 감이 아니라 정량적 근거가 필요하다. 30개 질의-정답 쌍을 미리 만들어두면, 어떤 변경을 하든 동일한 기준으로 비교할 수 있다.

### 5.2 설계 원칙

- **도메인 균등 배분**: 7개 도메인에 3~5개씩 배분하여 특정 도메인 편향 방지
- **질문 유형 다양화**: 유사 사례 검색(12), 트랙별 사례(6), 조건 패턴(6), 규제 쟁점(6)
- **gold_cases에 must_have 구분**: 핵심 사례(must_have=true)와 보조 사례를 분리하여, 핵심 사례 검색률(MH-Recall)을 별도 측정
- **negatives 포함**: 키워드는 비슷하지만 검색되면 안 되는 오답 사례를 지정하여 정밀도 측정
- **환경 독립성**: `case_id` 기반 매칭이라 임베딩 모델/벡터DB를 바꿔도 평가셋 수정 불필요

---

## 6. 1단계: 데이터 전략 비교

### 6.1 왜 데이터 전략부터 비교하는가

PDF 파싱 품질이 불균일하기 때문에, **같은 281건을 어떻게 가공해서 임베딩에 넣느냐**가 첫 번째이자 가장 큰 변수이다. 임베딩 모델을 아무리 좋은 걸로 바꿔도, 입력 데이터가 빈약하면 벡터 품질이 근본적으로 제한된다.

### 6.2 비교 전략 (3개)

| # | 전략 | content 구성 | 설계 의도 |
|---|------|-------------|----------|
| 1 | `structured` | service_name + service_description + special_provisions + pilot_scope + conditions | 핵심 필드만 넣으면 노이즈가 줄어 정밀도가 올라갈 수 있음 |
| 2 | `hybrid` | structured 기반 + structured < 100자인 65건은 full_text로 대체 | PDF 파싱이 부실한 65건을 원문으로 복구하면 커버리지가 올라갈 수 있음 |
| 3 | `fulltext` | 281건 모두 full_text만 사용 | 구조화 과정에서 정보 손실이 있을 수 있으니 원문 그대로가 나을 수 있음 |

### 6.3 결과

| 지표 | structured | hybrid | fulltext |
|------|-----------|--------|---------|
| **MH-Recall@5** | 0.861 | **0.889** | 0.672 |
| **Recall@5** | 0.786 | **0.830** | 0.597 |
| **MRR** | 0.911 | **0.917** | 0.717 |
| **Negative@5** | **0.20** | **0.20** | 0.35 |
| Neg Items | **9** | **9** | 14 |
| Latency P50 | 129ms | **122ms** | 129ms |

### 6.4 분석

1. **hybrid > structured > fulltext** 순서가 모든 핵심 지표에서 일관적
2. **fulltext 대폭 하락**: 원문 전체를 임베딩하면 머리글, 서식, 표 잔해 등 노이즈가 벡터를 오염시켜 검색 정밀도가 크게 떨어짐. Negative도 0.35로 최고 — 무관한 사례를 더 많이 검색
3. **hybrid의 structured 대비 우위**: 65건(FT_ONLY 50 + short 15)에 대한 full_text fallback 효과. 빈약한 structured 대신 원문을 넣으니 해당 사례들이 검색 가능해짐
4. **structured를 기반으로 선택한 이유**: hybrid가 소폭 우위이나, 65건의 문제를 "원문으로 대체"하는 것보다 "structured 필드를 채워주는 것(데이터 보강)"이 근본적 해결이라 판단

### 6.5 결론

> **structured 전략 확정**. hybrid가 소폭 우위이나, 100자 미만 65건(특히 FT_ONLY 50건)을 데이터 보강으로 해결하면 structured가 더 나은 기반이 된다.

---

## 7. 1.5단계: 데이터 보강 (FT_ONLY 50건)

### 7.1 왜 보강이 필요한가

1단계에서 structured 전략을 채택했지만, FT_ONLY 50건(18%)은 structured 필드가 완전히 비어있어 사실상 검색 불가능한 상태다. hybrid처럼 원문을 통째로 넣는 건 노이즈 문제가 있으므로, **"원문에서 핵심 정보만 추출해서 structured 필드를 채워주자"**는 접근을 택했다.

### 7.2 보강 방법

```bash
cd server && uv run python scripts/enrich_cases.py --apply --force
```

- **GPT-4o**로 `full_text`(PDF 원문)에서 structured 필드 5개를 추출:
  - `service_name`, `service_description`, `special_provisions`, `pilot_scope`, `conditions`
- 추출 결과: `server/eval/r2/enriched_50.json` (50건 검수용)
- 보강 적용 파일: `data/r2_data/cases_structured_enriched.json` (281건 전체)
- 원본 유지: `data/r2_data/cases_structured.json` (281건, 미보강)

### 7.3 보강 결과

- FT_ONLY: 50건(18%) → 3건(1%)
- 47건이 정상 structured content를 갖게 됨
- 나머지 3건은 PDF 원문 자체가 너무 짧아 추출 불가

### 7.4 gold_cases 전수 조사

데이터 보강으로 47건이 새롭게 검색 가능해지면서, 기존 gold_cases가 불완전해진다. 이전에는 검색 자체가 안 되던 사례가 이제 나타나기 때문에, 정답셋을 업데이트해야 공정한 비교가 가능하다. 50건 enriched 케이스 × 30개 쿼리를 클러스터링하여 전수 조사 실시.

**추가된 gold_cases: 20건 (6개 항목)**

| 항목 | 추가 건수 | 추가 사례 예시 |
|------|----------|---------------|
| R2-0008 | +1 | 임시허가_46_케이더봄 (비대면 진료) |
| R2-0010 | +2 | 실증특례_24_LG전자·서울대병원, 실증특례_23_LG전자·에임메드 |
| R2-0016 | +5 | 캠핑카 중개 클러스터 (어썸플랜, 지에스렌트카 등) |
| R2-0017 | +3 | 총회 전자의결 클러스터 (이보팅, 리빌드엑스, 이제이엠컴퍼니) |
| R2-0023 | +3 | PM 충전·주차 (포인테크 ID variant, LG전자, SKC) |
| R2-0028 | +6 | 스마트 보관 클러스터 (비즈하이브, 형동, 메타솔루션, 슈가맨, 에이블, 미니창고가방) |

### 7.5 보강 데이터 비교 결과 (gold-v2 태그)

| 지표 | structured | hybrid | fulltext | **enriched** |
|------|-----------|--------|---------|-------------|
| **MH-Recall@5** | 0.861 | 0.889 | 0.672 | **0.872** |
| **Recall@5** | 0.786 | 0.830 | 0.597 | **0.858** |
| **MRR** | 0.911 | 0.917 | 0.717 | **0.950** |
| **Negative@5** | 0.20 | 0.20 | 0.35 | **0.20** |
| Neg Items | 9 | 9 | 14 | **9** |
| Latency P50 | 129ms | 122ms | 129ms | **109ms** |
| Build Time | 4084ms | 3718ms | 9913ms | **4059ms** |

> `structured`, `hybrid`, `fulltext`: 원본 데이터(original) 사용
> `enriched`: 보강 데이터 + structured 전략 사용

### 7.6 핵심 비교: Original structured vs Enriched structured

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

### 7.7 결론

> **Enriched structured 전략 채택.**
>
> - Recall@5 **+7.3%**, MRR **+3.9%** 대폭 개선
> - hybrid 대비 MH-Recall만 소폭 열위(0.872 vs 0.889), Recall(+0.028)과 MRR(+0.033)에서 우위
> - FT_ONLY 50건 보강으로 근본적 데이터 품질 향상 달성
> - R2-0016 MH-Recall 회귀(0.50→0.00)는 향후 개선 과제

---

## 8. 2단계: 임베딩 모델 비교

### 8.1 왜 임베딩 모델을 비교하는가

1단계에서 데이터를 확정했으니, 다음은 **"이 데이터를 어떤 모델로 벡터화할 것인가"**이다. 같은 텍스트도 모델에 따라 벡터 공간에서의 표현이 달라지므로 검색 품질이 바뀔 수 있다. 특히 한국어 도메인 전문 용어(규제 샌드박스, 실증특례 등)를 잘 이해하는 모델이 유리할 수 있다.

### 8.2 실험 설정

| 항목 | 값 |
|------|-----|
| 고정 전략 | structured + enriched (1단계 승자) |
| Top-K | 5 |
| 평가셋 | 30개 (gold-v2) |
| 데이터 | 281건 (enriched) |

### 8.3 비교 모델 (4개)

| 코드 | 모델 | 유형 | 차원 | 비용 |
|------|------|------|------|------|
| E0 | text-embedding-3-small | OpenAI API | 1536 | $0.02/1M tokens |
| E1 | text-embedding-3-large | OpenAI API | 3072 | $0.13/1M tokens |
| E4 | BGE-M3 (BAAI) | 로컬 (GPU) | 1024 | 무료 (GPU 필요) |
| E5 | KURE-v1 (nlpai-lab) | 로컬 (GPU) | 1024 | 무료 (GPU 필요) |

### 8.4 결과

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

### 8.5 쿼리별 주요 차이

| 쿼리 | 승자 | 내용 |
|------|------|------|
| R2-0003 DRT 버스 | E4/E5 | Recall 1.0 + Neg 0.0 (E0는 스쿨버스 혼입, Neg 1.0) |
| R2-0030 공유주방 | E4/E5 | E0 완전 실패 (Recall 0.0) |
| R2-0016 캠핑카 | E4 | 유일하게 MH-R 1.0 |
| R2-0008 비대면 진료 | E0 | 유일하게 MH-R 1.0 (규제 쟁점 넓게 해석) |
| R2-0023 킥보드 충전 | 없음 | 4개 모델 모두 Neg 1.0 (구조적 한계) |

### 8.6 분석

1. **E4(BGE-M3)**: Recall 최강(0.883) + Negative 최저(0.133). 한국어 도메인 용어(공유주방, DRT 등)에서 강점. 단, 빌드 시간 250초(E0의 38배), GPU 서버 필요.
2. **E0(3-small)**: MRR 최강(0.950). 첫 번째 정답이 항상 높은 순위에 있어 사용자 체감 품질이 가장 좋음. API만으로 운영 가능, 빌드 6.5초.
3. **E1(3-large)**: 전 지표에서 E0/E4 사이. 차별화 포인트 없음.
4. **E5(KURE-v1)**: 레이턴시 최소(81ms)이나 MRR 최저(0.914). 빌드 751초로 실용성 부족.
5. **절대 성능 차이는 소폭**: Recall E4-E0 = +2.5%p, MRR E0-E4 = +2.2%p. R1/R3에서 모델 간 10%p 이상 차이가 났던 것과 대비됨.

> **왜 R2는 모델 간 차이가 작은가?** R2는 1건이 1문서이고 청킹이 없다. 문서 하나가 하나의 완결된 의미 단위여서, 어떤 모델로 벡터화해도 의미 표현의 차이가 크지 않다. 반면 R3 법령처럼 "한 문장에 여러 법적 개념이 압축된" 텍스트는 고차원 모델이 훨씬 유리하다.

### 8.7 청킹 필요성 판단

| 항목 | 값 |
|------|-----|
| structured 문서 max 길이 | 1,211자 (~807 tokens) |
| structured 문서 mean 길이 | 415자 (~277 tokens) |
| E0 토큰 한도 | 8,191 tokens |
| max 대비 한도 사용률 | ~10% |
| 토큰 초과 문서 수 | **0건 / 281건** |

> **청킹 불필요.** 가장 긴 문서도 토큰 한도의 10% 수준. 1건=1케이스 구조이므로 청킹 시 문맥 분산으로 Recall 저하 우려.

### 8.8 결론

> **E0 (text-embedding-3-small) 채택.**
>
> - MRR 0.950으로 사용자 체감 품질(첫 번째 정답 순위) 최강
> - API 키만으로 운영 가능 — GPU 서버 의존성 없음, 빌드 6.5초
> - E4 대비 Recall -2.5%p, Negative +6.7%p이나 절대 차이 소폭
> - 비용 E1의 1/6 ($0.02 vs $0.13 /1M tokens)
> - P95 레이턴시 913ms spike는 OpenAI API 네트워크 지연 (모델 품질과 무관)

---

## 9. 3단계: 생성 모델 비교

### 9.1 왜 생성 모델을 비교하는가

1~2단계는 **검색(Retrieval)** 품질을 최적화했다. 하지만 RAG 시스템의 최종 출력은 검색 결과가 아니라 **LLM이 생성한 답변**이다. 검색을 잘 해놓아도 LLM이 환각을 만들거나 질문에 엉뚱한 답을 하면 의미가 없다. 따라서 "검색된 문서를 기반으로 어떤 LLM이 가장 충실하고 적절한 답변을 생성하는가"를 비교한다.

### 9.2 실험 설정

| 항목 | 값 |
|------|-----|
| 고정 전략 | structured + enriched (1단계) |
| 고정 임베딩 | E0 text-embedding-3-small (2단계) |
| Top-K | 5 |
| 평가셋 | 30개 (gold-v2) |
| Judge 모델 | gpt-4.1 (RAGAS 평가자) |

### 9.3 비교 모델 (4개)

| 모델 | 유형 | 비용 |
|------|------|------|
| gpt-4o-mini | 4o 계열 소형 | 저 |
| gpt-4.1-mini | 4.1 계열 소형 | 저 |
| gpt-4o | 4o 계열 대형 | 중 |
| gpt-4.1 | 4.1 계열 대형 | 중 |

### 9.4 결과 (2026-02-23, 30항목)

| 지표 | gpt-4o-mini | gpt-4.1-mini | **gpt-4o** | gpt-4.1 |
|------|---|---|---|---|
| **Faithfulness** | 0.957 | 0.919 | **0.975** ★ | 0.942 |
| **Answer Relevancy** | 0.715 | 0.653 | **0.718** ★ | 0.627 |
| **MI Coverage** | **0.983** | 0.967 | **0.983** | 0.967 |
| **MNI Violation** | 0.0% | 0.0% | 0.0% | 0.0% |
| **Bullet Coverage** | 0.789 | 0.828 | 0.817 | **0.844** ★ |
| **Gen Latency P50** | 8,960ms | 4,175ms | **2,947ms** ★ | 3,573ms |

### 9.5 분석

1. **gpt-4o**: Faithfulness(0.975), Answer Relevancy(0.718), Latency(2.9s) **세 핵심 지표 모두 1위**
2. **gpt-4o-mini**: Faithfulness 0.957로 준수하나, 지연시간이 9.0초로 가장 느림 — mini가 더 느린 건 의외의 결과
3. **gpt-4.1**: Bullet Coverage 0.844로 핵심 포인트 커버율은 1위이나, Faithfulness가 0.942로 gpt-4o보다 3.3%p 낮음 — 환각 방지가 더 중요하므로 열위
4. **gpt-4.1-mini**: 전 지표에서 최하위권. Answer Relevancy 0.653으로 질문 적합성이 가장 낮음

### 9.6 결론

> **gpt-4o 채택.**
>
> - Faithfulness 0.975 — 검색 결과에 충실한 답변 비율 최고
> - Answer Relevancy 0.718 — 질문에 적절히 답변하는 비율 최고
> - Latency P50 2.9초 — 응답 속도 최고
> - Bullet Coverage만 gpt-4.1이 소폭 우위(+2.8%p)이나, Faithfulness 차이(3.3%p)가 더 중요

---

## 10. 4단계: 구성 튜닝

### 10.1 왜 구성 튜닝이 필요한가

모델과 데이터를 모두 확정한 뒤, 마지막으로 **검색→생성 파이프라인의 하이퍼파라미터**를 조정한다. "문서를 몇 개 가져올 것인가(top_k)"와 "유사도 점수가 낮은 결과를 걸러낼 것인가(threshold)"가 대상이다. top_k가 너무 작으면 정답을 놓치고, 너무 크면 노이즈가 유입되어 LLM 답변 품질이 떨어진다.

### 10.2 실험 범위

| 구성 | 범위 | 결과 |
|------|------|------|
| **Top-k 개수** | 3, 5, 7, 10 | **5 확정** |
| **Score threshold** | 0.2, 0.25, 0.3 | **불필요** (score 분포가 너무 좁음) |

### 10.3 Top-k Retrieval 비교 (2026-03-03, 30항목)

| 지표 | k=3 | **k=5** | k=7 | k=10 |
|------|-----|---------|-----|------|
| MH-Recall@K | 0.717 | **0.867** | 0.933 | 0.950 |
| Recall@K | 0.672 | **0.858** | 0.886 | 0.902 |
| MRR | 0.950 | **0.950** | 0.956 | 0.956 |
| Negative@K | 0.083 | **0.200** | 0.233 | 0.317 |
| Latency P50 | 131ms | 121ms | 130ms | 134ms |

> k 증가 시 Recall 상승 + Negative 상승 트레이드오프 관찰.
> - k=5→7: MH-R +6.7%p / Neg +3.3%p
> - k=7→10: MH-R +1.7%p / Neg +8.3%p (수확 체감, 노이즈 급증)

### 10.4 Score Threshold 실험 (k=7 고정)

| 지표 | threshold 없음 | 0.2 | 0.25 | 0.3 |
|------|---------------|-----|------|-----|
| MH-Recall@7 | **0.933** | 0.883 | 0.750 | 0.617 |
| Recall@7 | **0.886** | 0.825 | 0.706 | 0.547 |
| MRR | **0.956** | 0.922 | 0.889 | 0.722 |
| Negative@7 | 0.233 | 0.217 | 0.167 | **0.100** |

> **Score 분포**: min=0.076, median=0.297, max=0.584 (범위 너무 좁음).
> threshold=0.3에서 결과의 **52%가 필터링**되며 정답 문서까지 잘려나감.
> Negative 감소 효과보다 Recall 손실이 훨씬 큼 → **threshold 불필요**.

### 10.5 LLM 생성 비교: k=5 vs k=7

검색 지표에서는 k=7이 우위이므로, 실제 LLM 생성 품질까지 비교하여 최종 결정한다.

| 지표 | **k=5** (3단계 baseline) | k=7 |
|------|--------------------------|-----|
| MH-Recall | 0.867 | **0.933** |
| Faithfulness | **0.975** | 0.972 |
| Answer Relevancy | **0.718** | 0.634 |
| MI Coverage | 0.983 | **1.000** |
| Bullet Coverage | **0.817** | 0.794 |
| Gen Latency P50 | **2,947ms** | 4,847ms |

> k=7은 검색 품질 향상(MH-R +6.7%p)에도 불구하고 **생성 품질이 하락**:
> - Answer Relevancy **−8.4%p**: 추가 문서가 노이즈로 작용하여 답변 집중도 저하
> - Bullet Coverage **−2.2%p**
> - Latency **+64%**
>
> **결론**: 검색 지표만 보면 k=7이 좋아 보이지만, 실제 답변 품질까지 고려하면 k=5가 최적 균형점.

### 10.6 결론

> **top_k=5, threshold 없음 확정.**
>
> - k=5가 검색 품질과 생성 품질의 최적 균형점
> - k=7 이상은 retrieval 지표만 올리고 실제 답변 품질은 악화
> - Score threshold는 이 데이터의 score 분포(0.08~0.58)에서 효과 없음 — 어떤 값을 설정해도 정답까지 필터링됨

---

## 11. 5단계: 최종 확정 및 안정 구간

### 11.1 최종 확정 구성

```
원본 데이터:    승인 사례 PDF 281건 파싱 → cases_structured.json
데이터 전략:    structured + enriched (1단계)
임베딩 모델:    E0 text-embedding-3-small (2단계)
생성 모델:      gpt-4o (3단계)
청킹:           없음 (1건=1문서, max 1,211자)
top_k:          5 (4단계)
score threshold: 없음 (4단계)
```

### 11.2 안정 구간 정리

| 구성 요소 | 최적값 | 안정 구간 | 근거 |
|---|---|---|---|
| **데이터 전략** | structured + enriched | structured 계열 전체 | enriched가 전 지표 소폭 우위(MRR +0.04, R +0.07). fulltext는 큰 폭 하락 |
| **임베딩 모델** | E0 (3-small) | E0, E1, E4 모두 유사 | 절대 차이 ~2.5%p. E0이 MRR 최강 + API 전용 운영 이점 |
| **생성 모델** | gpt-4o | gpt-4o 단독 | Faith 0.975, Rel 0.718, Latency P50 2.9s로 전 지표 1위. 차순위 gpt-4o-mini는 Latency 3배 |
| **top_k** | 5 | **5~7 안정** | k=5: MH-R 0.867, k=7: 0.933. 단, k=7은 생성 시 Answer Relevancy −8.4%p 하락 → 검색+생성 균형은 k=5 |
| **threshold** | 없음 | **항상 없음** | Score 분포(0.08~0.58)가 너무 좁아 어떤 값이든 gold 결과를 먼저 필터링 |

### 11.3 전 단계 성능 요약 (확정 구성 기준)

| 지표 | 값 | 결정 단계 |
|------|-----|----------|
| MH-Recall@5 | 0.867 | 4단계 |
| Recall@5 | 0.858 | 4단계 |
| MRR | 0.950 | 4단계 |
| Negative@5 | 0.200 | 4단계 |
| Faithfulness | 0.975 | 3단계 |
| Answer Relevancy | 0.718 | 3단계 |
| MI Coverage | 0.983 | 3단계 |
| Bullet Coverage | 0.817 | 3단계 |
| Gen Latency P50 | 2,947ms | 3단계 |

### 11.4 Production 구축

Google Drive의 `cases_structured.json`을 enriched 데이터로 교체 후 실행:

```bash
cd server
uv run python scripts/collect_cases.py --strategy structured
```

- 컬렉션: `rag_cases` (281문서)
- Drive 파일이 enriched 내용이므로 별도 옵션 불필요

---

## 12. 핵심 교훈

### 12.1 데이터 품질 > 모델 교체

R2에서 가장 큰 성능 향상을 가져온 것은 임베딩 모델 교체(~2.5%p)가 아니라 **데이터 보강(enriched)**이었다(Recall +7.3%p, MRR +3.9%p). PDF 파싱 품질이 불균일한 현실에서, 비싼 모델로 바꾸는 것보다 데이터 자체를 개선하는 게 3배 효과적이었다.

### 12.2 검색 지표와 생성 지표는 다르다

top_k=7은 검색 지표(MH-Recall)에서 k=5보다 +6.7%p 높았지만, 실제 LLM 생성 품질(Answer Relevancy)은 −8.4%p 하락했다. 검색만 잘 하면 되는 게 아니라, LLM이 검색 결과를 어떻게 소화하는지까지 봐야 한다.

### 12.3 score threshold는 만능이 아니다

"유사도 낮은 결과를 걸러내면 정밀도가 올라갈 것"이라는 직관과 달리, score 분포가 좁은 데이터에서는 threshold가 정답까지 필터링한다. threshold 적용 전 score 분포를 반드시 먼저 확인해야 한다.

### 12.4 1건=1문서 데이터의 특성

R2처럼 문서 하나가 완결된 의미 단위인 경우, 임베딩 모델 간 차이가 매우 작다(~2.5%p). 청킹도 불필요하다. 반면 R3 법령처럼 문장 내 의미 밀도가 높은 데이터는 모델 간 차이가 10%p 이상 나타난다. 데이터 특성에 따라 최적화 전략이 달라져야 한다.

---

## 13. 결과 파일 목록

```
server/eval/r2/results/
├── retrieval/
│   ├── 2026-02-11_strategy_structured.json           # 1단계: Original, structured
│   ├── 2026-02-11_strategy_hybrid.json               # 1단계: Original, hybrid
│   ├── 2026-02-11_strategy_fulltext.json             # 1단계: Original, fulltext
│   ├── 2026-02-11_strategy_structured_enriched.json  # 1단계: Enriched, structured (채택)
│   ├── 2026-02-12_embedding_E0.json                  # 2단계: text-embedding-3-small (채택)
│   ├── 2026-02-12_embedding_E1.json                  # 2단계: text-embedding-3-large
│   ├── 2026-02-12_embedding_E4.json                  # 2단계: BGE-M3
│   ├── 2026-02-12_embedding_E5.json                  # 2단계: KURE-v1
│   ├── 2026-03-03_top_k_3.json                       # 4단계: k=3
│   ├── 2026-03-03_top_k_5.json                       # 4단계: k=5
│   ├── 2026-03-03_top_k_7.json                       # 4단계: k=7
│   ├── 2026-03-03_top_k_10.json                      # 4단계: k=10
│   ├── 2026-03-03_threshold_0.2.json                 # 4단계: threshold=0.2
│   ├── 2026-03-03_threshold_0.25.json                # 4단계: threshold=0.25
│   └── 2026-03-03_threshold_0.3.json                 # 4단계: threshold=0.3
└── llm/
    ├── 2026-02-23_generation_model_gpt-4o.json       # 3단계: gpt-4o (채택)
    ├── 2026-02-23_generation_model_gpt-4o-mini.json  # 3단계: gpt-4o-mini
    ├── 2026-02-23_generation_model_gpt-4.1.json      # 3단계: gpt-4.1
    ├── 2026-02-23_generation_model_gpt-4.1-mini.json # 3단계: gpt-4.1-mini
    └── 2026-03-03_top_k_7.json                       # 4단계: k=7 LLM 비교
```

모든 결과는 동일한 평가셋(gold-v2)으로 평가됨.

---

## 14. 파일 구조

```
server/
├── eval/
│   ├── metrics.py                        # 공통 Retrieval 지표
│   ├── llm_metrics.py                    # 공통 LLM-as-Judge 지표
│   └── r2/
│       ├── README.md                     # 평가셋 설계 + 워크플로우 상세
│       ├── evaluation_set.json           # 평가셋 (30개, gold-v2)
│       ├── enriched_50.json              # FT_ONLY 50건 GPT-4o 추출 결과
│       ├── common.py                     # 공용 유틸 (VectorStore, 지표)
│       ├── run_evaluation.py             # Retrieval 평가 스크립트
│       ├── run_llm_evaluation.py         # LLM Generation 평가 스크립트
│       ├── compare_results.py            # 결과 비교 스크립트
│       ├── configs/embedding.yaml        # 임베딩 모델 설정
│       └── results/
│           ├── retrieval/                # Retrieval 평가 결과 (15개 JSON)
│           └── llm/                      # LLM 평가 결과 (5개 JSON)
├── scripts/
│   ├── collect_cases.py                  # 데이터 수집 + Vector DB 저장
│   └── enrich_cases.py                   # FT_ONLY 보강 스크립트
└── data/r2_data/
    ├── cases_structured.json             # 원본 (281건, FT_ONLY 50건)
    └── cases_structured_enriched.json    # 보강본 (281건, FT_ONLY 3건)
```
