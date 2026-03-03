# R2 승인 사례 RAG 평가 및 성능 개선

## 개요

- **대상**: R2 승인 사례 RAG (ChromaDB `rag_cases` 컬렉션, 281건)
- **목적**: 데이터 전략·임베딩 모델·생성 구성을 바꿔가며 검색+생성 품질 비교
- **평가셋**: 30개 (`server/eval/r2/evaluation_set.json`)
- **원본 데이터**: `server/data/r2_data/cases_structured.json` (1개, 전략별 동적 변환)

---

## 성능 개선 워크플로우

```
[0단계] 평가셋 만들기 (30개)
    ↓
[1단계] 데이터 전략 비교 (임베딩 모델 고정)
    ↓
[2단계] 임베딩 모델 비교 (1단계 승자 전략 고정)
    ↓
[3단계] 생성 지표 테스트
    ↓
[4단계] 구성 튜닝 (Top-k, threshold 등)
    ↓
[5단계] 최종 확정 및 안정 구간 기록
```

### 0단계: 평가셋 만들기

- 30개 항목 작성 (`evaluation_set.json`)
- gold_cases의 case_id가 실제 데이터에 존재하는지 검증

### 1단계: 데이터 전략 비교 (R2 전용)

R2는 structured 필드 빈 비율이 높아(19~64%) **어떤 필드를 임베딩에 넣느냐**에 따라 성능이 크게 달라짐. 임베딩 모델은 현재 기본값(text-embedding-3-small)으로 고정하고 전략만 비교.

```bash
uv run python eval/r2/run_evaluation.py --strategy all
```

내부 흐름: 전략별 `create_documents(data, strategy)` → 임시 ChromaDB 컬렉션 생성 → 평가셋 30개 검색 → Recall 기록 → 컬렉션 삭제 → 다음 전략 → 비교표 출력

#### 비교 전략 (3개)

| # | 전략 | content 구성 | 특징 |
|---|---|---|---|
| 1 | `structured` (baseline) | service_name + service_description + special_provisions + pilot_scope + conditions | 유효 필드만 사용. 65건(23%)이 100자 미만 |
| 2 | `hybrid` | 1번 기반 + structured < 100자인 65건은 full_text로 대체 | 커버리지 100% |
| 3 | `fulltext` | 281건 모두 full_text만 사용 | structured 무시, 원문 전체 임베딩 |

> **baseline 변경사항**: conditions(44.8% 존재, 항목당 28자 × 평균 5.7개) 추가. current_regulation(98.9% 빈값), expected_effect(99.3% 빈값), review_result/project_overview(3건뿐) 제거.

#### 비교 논리

| 비교 | 측정 대상 |
|---|---|
| 1 vs 2 | 65건 full_text fallback 효과 (빈약한 데이터 복구가 도움되는가?) |
| 1 vs 3 | structured 큐레이션 vs 원문 전체, 어느 쪽이 검색에 유리한가? |
| 2 vs 3 | 하이브리드가 full-text only보다 나은가? (구조화 정보의 가치) |

#### 필드별 임베딩 여부

| 필드 | 빈 비율 | 1. structured | 2. hybrid | 3. fulltext |
|---|---|---|---|---|
| `track` (라벨) | 0% | ✅ | ✅ | ❌ (full_text에 포함) |
| `service_name` | 30.6% | ✅ | ✅ | ❌ |
| `company_name` | 0% | ✅ | ✅ | ❌ |
| `service_description` | 49.8% | ✅ | ✅ | ❌ |
| `special_provisions` | 19.2% | ✅ | ✅ | ❌ |
| `current_regulation` | 98.9% | ❌ | ❌ | ❌ |
| `expected_effect` | 99.3% | ❌ | ❌ | ❌ |
| `pilot_scope` | 64.4% | ✅ | ✅ | ❌ |
| `conditions` | 55.2% | ✅ | ✅ | ❌ |
| `full_text` | 0% | ❌ | ✅ (65건만) | ✅ (281건 전체) |

### 2단계: 임베딩 모델 비교

1단계 승자 전략을 고정하고, 임베딩 모델만 교체하며 비교.

```bash
uv run python eval/r2/run_evaluation.py --strategy {1단계 승자} --model all
```

| 모델 | 유형 | 한국어 nDCG@1 |
|---|---|---|
| text-embedding-3-small (현재) | API | ~0.47 |
| text-embedding-3-large | API | 0.517 |
| KURE-v1 | 셀프호스팅 | 0.606 |
| BGE-M3 | 셀프호스팅 | 0.598 |

### 3단계: 생성 모델 비교

1~2단계 확정 조합(structured + enriched + E0)으로, 전체 30개 항목에 대해 생성 품질 비교.

```bash
uv run python eval/r2/run_llm_evaluation.py --model all --tags stage3
```

#### 비교 모델 (4개)

| 모델 | 유형 | 비용 |
|---|---|---|
| gpt-4o-mini | 4o 계열 소형 | 저 |
| gpt-4.1-mini | 4.1 계열 소형 | 저 |
| gpt-4o | 4o 계열 대형 | 중 |
| gpt-4.1 | 4.1 계열 대형 | 중 |

#### 평가 지표

| 지표 | 설명 | 평가 방식 |
|---|---|---|
| Faithfulness | 응답이 컨텍스트에 기반하는지 (환각 방지) | RAGAS (gpt-4.1 Judge) |
| Answer Relevancy | 응답이 질문에 적절히 답변하는지 | RAGAS (gpt-4.1 Judge) |
| Must-Include Coverage | `must_include` 키워드 포함 비율 | 문자열 매칭 |
| Must-Not-Include Violation | `must_not_include` 키워드 위반 여부 | 문자열 매칭 |
| Bullet Coverage | `expected_answer_bullets` 핵심 포인트 커버 비율 | LLM Judge (gpt-4.1) |

#### 3단계 결과 (2026-02-23, 30항목)

| 지표 | gpt-4o-mini | gpt-4.1-mini | **gpt-4o** | gpt-4.1 |
|---|---|---|---|---|
| Faithfulness | 0.957 | 0.919 | **0.975** ★ | 0.942 |
| Answer Relevancy | 0.715 | 0.653 | **0.718** ★ | 0.627 |
| MI Coverage | **0.983** | 0.967 | **0.983** | 0.967 |
| MNI Violation | 0.0% | 0.0% | 0.0% | 0.0% |
| Bullet Coverage | 0.789 | 0.828 | 0.817 | **0.844** ★ |
| Gen Latency P50 | 8,960ms | 4,175ms | **2,947ms** ★ | 3,573ms |

> **결론**: gpt-4o가 Faithfulness·Answer Relevancy·Latency 모두 1위. Bullet Coverage만 gpt-4.1이 소폭 우위(+2.8%p)이나 Faithfulness 차이(3.3%p)가 더 크므로 **gpt-4o 채택**.

### 4단계: 구성 튜닝

확정된 조합(structured + enriched + E0 + gpt-4o) 위에서, 검색→생성 파이프라인 구성을 바꿔가며 최적화.

#### 실험 범위

| 구성 | 범위 | 결과 |
|---|---|---|
| **Top-k 개수** | 3, 5, 7, 10 | **5 확정** (아래 참고) |
| **Score threshold** | 0.2, 0.25, 0.3 | **불필요** (score 분포가 너무 좁음) |
| 중복 제거 (deduplicate) | — | 해당 없음 (임시 컬렉션에 중복 없음) |
| Chunk ordering | — | 해당 없음 (R2는 청킹 없음) |
| 요약 vs 원문 | — | 5단계에서 고려 |

#### 4단계-1: Top-k Retrieval 비교 (2026-03-03, 30항목)

| 지표 | k=3 | **k=5** | k=7 | k=10 |
|---|---|---|---|---|
| MH-Recall@K | 0.7167 | **0.8667** | 0.9333 | 0.9500 |
| Recall@K | 0.6717 | **0.8581** | 0.8860 | 0.9019 |
| MRR | 0.9500 | **0.9500** | 0.9556 | 0.9556 |
| Negative@K | 0.0833 | **0.2000** | 0.2333 | 0.3167 |
| Latency P50 | 131ms | 121ms | 130ms | 134ms |

> k 증가 시 Recall 상승 + Negative 상승 트레이드오프 관찰. k=5→7에서 MH-R +6.7%p / Neg +3.3%p, k=7→10에서 MH-R +1.7%p / Neg +8.3%p.

#### 4단계-2: Score Threshold 실험 (k=7 고정)

| 지표 | threshold 없음 | 0.2 | 0.25 | 0.3 |
|---|---|---|---|---|
| MH-Recall@7 | **0.9333** | 0.8833 | 0.7500 | 0.6167 |
| Recall@7 | **0.8860** | 0.8249 | 0.7057 | 0.5472 |
| MRR | **0.9556** | 0.9222 | 0.8889 | 0.7222 |
| Negative@7 | 0.2333 | 0.2167 | 0.1667 | **0.1000** |

> **Score 분포**: min=0.076, median=0.297, max=0.584 (범위 너무 좁음). threshold=0.3에서 결과의 52%가 필터링됨. Negative 감소 효과보다 Recall 손실이 훨씬 큼 → **threshold 불필요**.

#### 4단계-3: LLM 생성 비교 (k=5 vs k=7, gpt-4o)

| 지표 | **k=5** (3단계 baseline) | k=7 |
|---|---|---|
| MH-Recall | 0.8667 | **0.9333** |
| Faithfulness | **0.9749** | 0.9718 |
| Answer Relevancy | **0.7177** | 0.6337 |
| MI Coverage | 0.9833 | **1.0000** |
| Bullet Coverage | **0.8167** | 0.7944 |
| Gen Latency P50 | **2,947ms** | 4,847ms |

> k=7은 검색 품질 향상(MH-R +6.7%p)에도 불구하고 생성 품질이 하락. Answer Relevancy −8.4%p, Bullet Coverage −2.2%p, Latency +64%. 추가 context가 노이즈로 작용하여 응답 집중도가 떨어짐.

#### 4단계 결론

> **top_k=5, threshold 없음 확정**. 검색 품질과 생성 품질의 균형점이 k=5. k=7 이상은 retrieval 지표만 올리고 실제 답변 품질은 악화. Score threshold는 이 데이터의 score 분포(0.08~0.58)에서 효과 없음.

### 5단계: 최종 확정 및 안정 구간 기록 (2026-03-03)

#### 최종 확정 구성

```
데이터 전략:   structured + enriched (1단계)
임베딩 모델:   E0 text-embedding-3-small (2단계)
생성 모델:     gpt-4o (3단계)
청킹:          없음 (1건=1문서, max 1,211자)
top_k:         5 (4단계)
score threshold: 없음 (4단계)
```

#### 안정 구간 정리

| 구성 요소 | 최적값 | 안정 구간 | 근거 |
|---|---|---|---|
| **데이터 전략** | structured + enriched | structured 계열 전체 | enriched가 전 지표 소폭 우위(MRR +0.04, R +0.07). fulltext는 큰 폭 하락 |
| **임베딩 모델** | E0 (3-small) | E0, E1, E4 모두 유사 | 절대 차이 ~2.5%p. E0이 MRR 최강 + API 전용 운영 이점 |
| **생성 모델** | gpt-4o | gpt-4o 단독 | Faith 0.975, Rel 0.718, Latency P50 2.9s로 전 지표 1위. 차순위 gpt-4o-mini는 Latency 3배 |
| **top_k** | 5 | **5~7 안정** | k=5: MH-R 0.867, k=7: 0.933. 단, k=7은 생성 시 Answer Relevancy −8.4%p 하락 → 검색+생성 균형은 k=5 |
| **threshold** | 없음 | **항상 없음** | Score 분포(0.08~0.58)가 너무 좁아 어떤 값이든 gold 결과를 먼저 필터링 |

#### 전 단계 성능 요약 (확정 구성 기준)

| 지표 | 값 | 단계 |
|---|---|---|
| MH-Recall@5 | 0.867 | 4단계 |
| Recall@5 | 0.858 | 4단계 |
| MRR | 0.950 | 4단계 |
| Negative@5 | 0.200 | 4단계 |
| Faithfulness | 0.975 | 3단계 |
| Answer Relevancy | 0.718 | 3단계 |
| MI Coverage | 0.983 | 3단계 |
| Bullet Coverage | 0.817 | 3단계 |
| Gen Latency P50 | 2,947ms | 3단계 |

#### Production ChromaDB 구축

Google Drive의 `cases_structured.json`을 enriched 데이터로 교체 후 실행:

```bash
cd server
uv run python scripts/collect_cases.py --strategy structured
```

- 컬렉션: `rag_cases` (281문서)
- Drive 파일이 enriched 내용이므로 별도 옵션 불필요

---

## 평가셋 설계

### 평가 항목 구조

```json
{
  "id": "R2-0001",
  "category": "healthcare",
  "query_type": "similar_case",
  "data_quality": "normal",
  "question": "반려동물 건강 모니터링을 AI로 하려는데, 비슷한 승인 사례가 있나요?",
  "gold_cases": [
    {
      "case_id": "실증특례_100_에이아이포펫",
      "track": "실증특례",
      "service_name": "AI를 활용한 수의사의 반려동물 건강상태 모니터링 서비스",
      "must_have": true
    }
  ],
  "negatives": [
    {
      "case_id": "실증특례_101_이제이엠컴퍼니",
      "reason": "같은 ICT 샌드박스이지만 전자투표 서비스로 도메인 무관"
    }
  ],
  "expected_answer_bullets": [
    "반려동물 비대면 진료/모니터링 관련 실증특례 사례 존재",
    "안과 질환 등 제한된 범위에서 실증 진행",
    "수의사법 상 직접 진료 규제가 쟁점"
  ],
  "must_include": ["비대면", "모니터링", "실증특례"],
  "must_not_include": ["승인 사례 없음"],
  "notes": "동물 헬스케어 도메인. 서비스 유사도 + 규제 쟁점 유사도 모두 검증."
}
```

### 필드 정의

| 필드 | 타입 | 설명 | 평가 용도 |
|---|---|---|---|
| `id` | string | 고유 ID (R2-0001~R2-0030) | 식별 |
| `category` | string | 도메인 카테고리 | 도메인별 성능 분석 |
| `query_type` | string | 검색 유형 | 시나리오별 성능 분석 |
| `data_quality` | string | `normal` / `full_text_only` | 개선 효과 측정 |
| `question` | string | 현업 표현의 검색 질문 | 검색 입력 |
| `gold_cases` | array | 정답 사례 목록 | Retrieval 평가 (Recall@K) |
| `gold_cases[].must_have` | boolean | 핵심 사례 여부 | Must-Have Recall |
| `negatives` | array | 검색되면 안 되는 사례 | 정밀도 평가 |
| `expected_answer_bullets` | array | 예상 답변 포인트 | Generation 평가 |
| `must_include` | array | 답변 필수 키워드 | 답변 품질 |
| `must_not_include` | array | 답변 금지 키워드 | 환각 방지 |
| `notes` | string | 평가 의도/맥락 | 디버깅용 |

### 분류 기준

**category (도메인)**

| 카테고리 | 예시 서비스 | 배분 |
|---|---|---|
| `mobility` | 자율주행, 킥보드, 드론 배달 | 5개 |
| `healthcare` | 원격진료, AI 진단, 반려동물 | 5개 |
| `fintech` | 간편결제, P2P, 가상자산 | 5개 |
| `platform` | 캠핑카 중개, 총회 전자의결 | 5개 |
| `energy` | 전력중개, ESS, EV충전 | 4개 |
| `logistics` | 배달로봇, 물류드론 | 3개 |
| `etc` | 부동산, 스마트홈, 기타 | 3개 |

**query_type (검색 유형)**

| 유형 | 설명 | 질문 예시 | 배분 |
|---|---|---|---|
| `similar_case` | 유사 사례 검색 | "자율주행 배달 로봇 관련 승인 사례?" | 12개 |
| `track_specific` | 특정 트랙 사례 | "임시허가로 승인된 핀테크 사례?" | 6개 |
| `condition_pattern` | 조건/부가조건 패턴 | "드론 배달 실증특례의 부가조건은?" | 6개 |
| `regulation_issue` | 규제 쟁점 기반 | "개인정보 이슈로 샌드박스 승인받은 사례?" | 6개 |

**data_quality (데이터 품질)**

| 값 | 기준 | 해당 건수 | 배분 | 측정 대상 |
|---|---|---|---|---|
| `normal` | structured content >= 100자 | 216건 (77%) | 28개 | 임베딩 모델 교체 효과 |
| `full_text_only` | structured content < 100자 | 65건 (23%, FT_ONLY 50 + short 15) | 2개 | 하이브리드 fallback 효과 |

### gold_cases 작성 기준

| must_have | 기준 | 예시 |
|---|---|---|
| `true` | 질문의 핵심 서비스와 직접 관련된 사례 | "AI 반려동물 모니터링" → 에이아이포펫 |
| `false` | 같은 도메인이나 유사 규제 쟁점의 보조 사례 | "AI 반려동물 모니터링" → 다른 비대면 진료 사례 |

- `must_have: true`: 질문당 1~2개
- `must_have: false`: 질문당 1~2개
- 합계: 질문당 2~3개

### negatives 작성 기준

| 유형 | 설명 | 예시 |
|---|---|---|
| 같은 도메인, 다른 서비스 | 키워드 겹치지만 핵심 다름 | "AI 건강 모니터링" → "AI 교육 서비스" |
| 같은 트랙, 다른 도메인 | 트랙만 같고 내용 무관 | 실증특례 헬스케어 질문 → 실증특례 모빌리티 사례 |
| 유사 키워드, 다른 맥락 | OCR 노이즈 오매칭 테스트 | 키워드만 일치하는 OCR 깨진 사례 |

- 권장: 질문당 1~2개

### 질문 작성 가이드

좋은 예:
- "자율주행 배달 로봇 서비스를 시작하려는데 비슷한 승인 사례가 있나요?"
- "원격으로 환자 모니터링하는 서비스가 실증특례 받은 적 있나요?"
- "캠핑카 공유 플랫폼인데 규제 샌드박스 통과한 사례가 궁금합니다"

나쁜 예:
- "실증특례_100_에이아이포펫 사례 알려줘" → case_id 직접 언급
- "승인 사례 알려줘" → 너무 모호
- "2023-9호 지정 건에 대해" → 지정번호로 검색 (RAG 목적 아님)

---

## 환경 독립성

| 변경 항목 | 평가셋 수정 필요? | 이유 |
|---|---|---|
| 임베딩 모델 교체 | 없음 | `case_id` 기반 매칭 |
| 데이터 전략 변경 | 없음 | `case_id`는 원본 JSON 고유값 |
| 벡터DB 교체 (ChromaDB → 다른 DB) | 없음 | 추상화된 인터페이스 사용 |
| 원본 데이터 추가/삭제 | 있음 | gold_cases의 case_id가 없어지면 수정 필요 |

### 매칭 로직

```python
retrieved_case_ids = {r.metadata["case_id"] for r in search_results}
gold_case_ids = {g["case_id"] for g in eval_item["gold_cases"]}

recall = len(retrieved_case_ids & gold_case_ids) / len(gold_case_ids)
```

---

## 평가 지표

### Retrieval 평가 (run_evaluation.py)

| 지표 | 설명 |
|---|---|
| Recall@5 | Top-5 안에 gold 사례 포함 비율 |
| Recall@10 | Top-10 안에 gold 사례 포함 비율 |
| MRR | 첫 번째 gold 사례의 역순위 (1 / rank) |
| Must-Have Recall | `must_have: true` 사례만의 Recall |
| Negative@K | Top-K 안에 negative 사례 포함 비율 (낮을수록 좋음) |

### Generation 평가 (run_llm_evaluation.py)

| 지표 | 설명 | 평가 방식 |
|---|---|---|
| Faithfulness | 응답이 컨텍스트에 기반하는지 (환각 방지) | RAGAS LLM Judge |
| Answer Relevancy | 응답이 질문에 적절히 답변하는지 | RAGAS LLM Judge |
| Must-Include Coverage | `must_include` 키워드 포함 비율 | 문자열 매칭 |
| Must-Not-Include Violation | `must_not_include` 키워드 포함 여부 | 문자열 매칭 |
| Bullet Coverage | `expected_answer_bullets` 핵심 포인트 커버 비율 | LLM Judge |

---

## 파일 구조

```
server/
├── eval/
│   ├── __init__.py
│   ├── metrics.py                    # [공통] Retrieval 지표 계산
│   ├── llm_metrics.py                # [공통] LLM-as-Judge 지표
│   ├── r2/
│   │   ├── __init__.py
│   │   ├── README.md                 # 이 문서
│   │   ├── evaluation_set.json       # 평가셋 (30개)
│   │   ├── run_evaluation.py         # Retrieval 평가 (--strategy, --model)
│   │   ├── run_llm_evaluation.py     # LLM-as-Judge 평가
│   │   └── results/
│   │       ├── retrieval/
│   │       │   └── {날짜}_{전략}_{모델}.json
│   │       └── llm/
│   │           └── {날짜}_{변경요소}.json
│   └── r3/
│       └── (동일 구조)
├── scripts/
│   └── collect_cases.py              # --strategy 파라미터 (structured/hybrid/fulltext)
└── data/
    └── r2_data/
        └── cases_structured.json     # enriched 데이터 (Google Drive에서 다운로드)
```

---

## 전체 To-Do

### 0단계: 평가셋

- [x] R2 평가셋 30개 작성
- [x] gold_cases case_id 검증

### 1단계: 데이터 전략

- [x] collect_cases.py에 --strategy 파라미터 추가 + conditions 필드 baseline 포함
- [x] run_evaluation.py에 --strategy all 구현
- [x] `uv run python eval/r2/run_evaluation.py --strategy all` 실행
- [x] 1등 데이터 전략 확정 → **structured + enriched**

### 2단계: 임베딩 모델

- [x] KURE-v1 / BGE-M3 로컬 실행 환경 구성
- [x] run_evaluation.py에 --embedding 옵션 구현 (E0/E1/E4/E5/all)
- [x] `uv run python eval/r2/run_evaluation.py --data-version enriched --embedding all --tags stage2` 실행
- [x] 1등 임베딩 모델 확정 → **E0 (text-embedding-3-small) 채택**

### 3단계: 생성 모델 비교

- [x] run_llm_evaluation.py 생성 (Retrieval + Generation + R2 고유 지표 통합)
- [x] llm_metrics.py RAGAS >=0.4 호환 업데이트
- [x] compare_results.py --llm 플래그 추가
- [x] gpt-4o-mini 기준선 측정 (30항목)
- [x] 4개 모델 전체 비교 (gpt-4o-mini, gpt-4.1-mini, gpt-4o, gpt-4.1)
- [x] 생성 모델 확정 → **gpt-4o 채택**

### 4단계: 구성 튜닝

- [x] Top-k 비교 (3, 5, 7, 10) → k=5 확정
- [x] Score threshold 실험 (0.2, 0.25, 0.3) → 불필요 확정
- [x] k=7 LLM 생성 비교 → k=5가 생성 품질 우위
- [x] `run_evaluation.py`에 `--threshold` 옵션 추가
- [x] `run_llm_evaluation.py`에 `--threshold` 옵션 추가
- [x] 최적 조건 확정: **top_k=5, threshold 없음**

### 5단계: 마무리

- [x] 안정 구간 정리
- [x] Google Drive `cases_structured.json`을 enriched 데이터로 교체
- [x] `collect_cases.py --strategy structured`로 production ChromaDB 구축 (281문서)
- [x] 결과 문서화
