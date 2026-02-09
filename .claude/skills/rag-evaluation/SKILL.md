---
name: rag-evaluation
description: "RAG 시스템 평가셋 작성 및 평가 수행 가이드. RAG 성능 측정, 평가셋 생성, Retrieval/Generation 품질 평가 시 사용. 트리거 - RAG 평가, 청킹 전략 비교, 임베딩 모델 비교, 검색 품질 측정"
---

# RAG Evaluation Guide

RAG(Retrieval-Augmented Generation) 시스템의 평가셋 작성 및 평가 수행 가이드.

## 평가셋 위치

```text
server/
├── eval/                     # 평가 관련 (git 추적)
│   └── r3/
│       └── evaluation_set.json
└── data/                     # 데이터 (gitignore)
    └── r3_data/
        └── chunks.json       # 청킹 결과 (평가 시 참조)
```

## 평가셋 구조

### 기본 구조

```json
{
  "version": "3.0",
  "description": "R3 도메인별 규제/법령 RAG 평가셋",
  "total_count": 10,
  "evaluation_items": [...]
}
```

### 평가 항목 구조

```json
{
  "id": "R3-0001",
  "domain": "finance",
  "question": "간편결제 서비스에서 부정결제 사고가 발생하면 책임은 누가 지나요?",

  "gold_citations": [
    {
      "law_name": "전자금융거래법",
      "article_no": "9",
      "paragraph_no": "①",
      "must_have": true
    }
  ],

  "negatives": [
    {
      "law_name": "신용정보의 이용 및 보호에 관한 법률",
      "article_no": "32",
      "paragraph_no": "①"
    }
  ],

  "expected_answer_bullets": [
    "원칙적으로 금융회사 또는 전자금융업자가 책임을 부담",
    "이용자의 고의 또는 중과실이 있는 경우 예외"
  ],

  "must_include": ["금융회사", "책임", "고의 또는 중과실"],
  "must_not_include": ["이용자가 무조건 책임"],

  "notes": "제9조(책임) 기반 질의. 원칙과 예외 조건 구분이 핵심."
}
```

### 필드 설명

| 필드                         | 설명                         | 용도                      |
| ---------------------------- | ---------------------------- | ------------------------- |
| `gold_citations`             | 정답 근거 청크들             | Retrieval 평가 (Recall@K) |
| `gold_citations[].must_have` | 핵심 근거 여부               | 핵심근거 Recall 측정      |
| `negatives`                  | 오답 근거 청크들             | 재랭킹/정확도 평가        |
| `expected_answer_bullets`    | 예상 답변 포인트             | Generation 평가           |
| `must_include`               | 답변에 포함되어야 할 키워드  | 답변 품질 평가            |
| `must_not_include`           | 답변에 포함되면 안 되는 내용 | 환각 방지 평가            |
| `notes`                      | 평가 의도/맥락               | 디버깅/분석용             |

## 청킹 데이터 구조

### chunks.json 구조

```json
{
  "total_count": 3184,
  "chunks": [
    {
      "chunk_id": "law_280277_9_1",
      "content": "[전자금융거래법] 제9조(금융회사 또는 전자금융업자의 책임)\n① ...",
      "metadata": {
        "source_type": "law",
        "law_name": "전자금융거래법",
        "law_mst": "280277",
        "article_no": "9",
        "article_title": "금융회사 또는 전자금융업자의 책임",
        "paragraph_no": "①",
        "chunk_type": "paragraph",
        "citation": "전자금융거래법 제9조 ①",
        "domain": "finance",
        "domain_label": "금융",
        "ministry": "금융위원회",
        "enforcement_date": "20251001"
      }
    }
  ]
}
```

### 청킹 데이터 저장

각 collect 스크립트 실행 시 Vector DB 저장과 함께 청크 JSON이 자동 생성됩니다.

```bash
cd server
uv run python scripts/collect_laws.py        # → data/r3_data/chunks.json
uv run python scripts/collect_cases.py       # → data/r2_data/chunks.json
uv run python scripts/collect_regulations.py # → data/r1_data/chunks.json
```

공통 유틸리티: `app/db/export.py`의 `save_chunks_json()` 함수 사용

## 평가셋 ↔ 청크 매칭

### 매칭 로직

평가 시 `gold_citations`와 `chunks.json`을 매칭하는 로직:

```python
def find_matching_chunks(citation: dict, chunks: list[dict]) -> list[dict]:
    """평가셋 citation과 매칭되는 청크 찾기"""
    matches = []

    for chunk in chunks:
        m = chunk['metadata']

        # 필수 필드 매칭
        if m['law_name'] != citation.get('law_name'):
            continue
        if m['article_no'] != citation.get('article_no'):
            continue
        if m['paragraph_no'] != citation.get('paragraph_no'):
            continue

        # article_title 있으면 추가 검증 (같은 조에 여러 조항 있는 경우)
        if citation.get('article_title'):
            if m.get('article_title') != citation['article_title']:
                continue

        matches.append(chunk)

    return matches
```

### 산업융합촉진법 제10조 주의사항

같은 조에 여러 조항이 있는 경우 `article_title`로 구분 필요:

```json
// 규제 신속확인
{"law_name": "산업융합 촉진법", "article_no": "10", "article_title": "규제 신속확인"}

// 실증을 위한 규제특례
{"law_name": "산업융합 촉진법", "article_no": "10", "article_title": "실증을 위한 규제특례"}
```

## 평가 지표

### Retrieval 평가

| 지표             | 설명                            | 수식                              |
| ---------------- | ------------------------------- | --------------------------------- |
| Recall@K         | Top-K 안에 gold 청크 포함 비율  | `\|Retrieved ∩ Gold\| / \|Gold\|` |
| Precision@K      | Top-K 중 gold 청크 비율         | `\|Retrieved ∩ Gold\| / K`        |
| MRR              | 첫 번째 gold 청크의 역순위      | `1 / rank_of_first_gold`          |
| Must-Have Recall | `must_have=true` 청크 포함 비율 | 핵심 근거 검색 성능               |

### Generation 평가

| 지표                       | 설명                                       |
| -------------------------- | ------------------------------------------ |
| Must-Include Coverage      | `must_include` 키워드 포함 비율            |
| Must-Not-Include Violation | `must_not_include` 키워드 포함 여부        |
| Expected Bullets Coverage  | `expected_answer_bullets` 포인트 커버 비율 |

### Negative 활용

```python
def evaluate_with_negatives(retrieved_chunks, gold_citations, negatives):
    """Negative를 활용한 정밀 평가"""

    gold_ids = get_chunk_ids(gold_citations)
    negative_ids = get_chunk_ids(negatives)

    # Negative가 상위에 랭크되면 감점
    for i, chunk in enumerate(retrieved_chunks):
        if chunk['chunk_id'] in negative_ids:
            penalty = 1 / (i + 1)  # 상위일수록 큰 감점

    # Gold가 Negative보다 높은 순위인지 확인
    # ...
```

## 평가 시나리오

### 1. 청킹 전략 비교

```python
strategies = ['paragraph', 'article', 'semantic', 'sliding_window']

for strategy in strategies:
    chunks = load_chunks(f'chunks_{strategy}.json')
    results = evaluate_retrieval(evaluation_set, chunks)
    print(f'{strategy}: Recall@5={results["recall@5"]:.3f}')
```

### 2. 임베딩 모델 비교

```python
models = ['text-embedding-3-small', 'text-embedding-3-large', 'multilingual-e5']

for model in models:
    vector_store = create_vector_store(chunks, model)
    results = evaluate_retrieval(evaluation_set, vector_store)
    print(f'{model}: MRR={results["mrr"]:.3f}')
```

### 3. 재랭커 효과 측정

```python
# Without reranker
results_base = evaluate_retrieval(evaluation_set, vector_store, top_k=10)

# With reranker
results_reranked = evaluate_retrieval(
    evaluation_set,
    vector_store,
    top_k=10,
    reranker=cohere_reranker
)

print(f'Base: Recall@5={results_base["recall@5"]:.3f}')
print(f'Reranked: Recall@5={results_reranked["recall@5"]:.3f}')
```

## 평가셋 작성 팁

### 좋은 질문 작성

```text
# 좋은 예
- "간편결제 서비스에서 부정결제 사고가 발생하면 책임은 누가 지나요?"
- "원격의료는 어떤 경우에 허용되나요?"

# 피해야 할 예
- "전자금융거래법 제9조가 뭐야?" (조문 번호 직접 언급)
- "책임에 대해 알려줘" (너무 모호함)
```

### Negative 선정 기준

1. **같은 법령, 다른 주제**: 키워드 유사하지만 다른 조항
2. **유사 법령, 같은 주제**: 개인정보보호법 vs 신용정보법
3. **같은 도메인, 관련 없는 조항**: 절차 vs 정의 조항

### must_have 판단 기준

- `must_have: true` - 질문에 직접 답변하는 핵심 조항
- `must_have: false` - 맥락 제공, 보조 정보 조항

## 환경 독립성

이 평가셋 구조는 다음 변경에도 동일하게 사용 가능:

| 변경 항목     | 영향 | 이유                           |
| ------------- | ---- | ------------------------------ |
| 청킹 전략     | 없음 | metadata 기반 매칭             |
| 임베딩 모델   | 없음 | 평가셋은 모델 독립적           |
| Vector DB     | 없음 | 추상화된 인터페이스 사용       |
| 법령 업데이트 | 일부 | `article_no` 변경 시 수정 필요 |

## 관련 파일

| 파일        | 경로                                            | 설명                      |
| ----------- | ----------------------------------------------- | ------------------------- |
| 평가셋      | `server/eval/r3/evaluation_set.json`            | R3 RAG 평가셋             |
| 청크 데이터 | `server/data/{r1,r2,r3}_data/chunks.json`       | 청킹 결과 (gitignore)     |
| 공통 유틸   | `server/app/db/export.py`                       | 청크 JSON 저장 함수       |
| R3 수집     | `server/scripts/collect_laws.py`                | 법령 수집 + 청크 저장     |
| R2 수집     | `server/scripts/collect_cases.py`               | 승인사례 수집 + 청크 저장 |
| R1 수집     | `server/scripts/collect_regulations.py`         | 규제제도 수집 + 청크 저장 |
| RAG Tool    | `server/app/tools/shared/rag/domain_law_rag.py` | R3 검색 도구              |
