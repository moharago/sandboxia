---
name: rag-evaluation
description: "RAG 시스템 평가셋 작성 및 평가 수행 가이드. RAG 성능 측정, 평가셋 생성, Retrieval/Generation 품질 평가 시 사용. 트리거 - RAG 평가, 청킹 전략 비교, 임베딩 모델 비교, 검색 품질 측정"
---

# RAG Evaluation Guide

RAG(Retrieval-Augmented Generation) 시스템의 평가셋 작성 및 평가 수행 가이드.

## 파일 구조

```text
server/
├── eval/                           # 평가 관련 (git 추적)
│   ├── __init__.py
│   ├── metrics.py                  # 공통 지표 계산 함수
│   └── r3/
│       ├── __init__.py
│       ├── evaluation_set.json     # R3 평가셋 (30개 항목)
│       ├── run_evaluation.py       # R3 평가 스크립트
│       └── results/                # 평가 결과 저장
│           └── {날짜}_{변경요소}_{값}.json
└── data/                           # 데이터 (gitignore)
    └── r3_data/
        └── chunks.json             # 청킹 결과 (평가 시 참조)
```

## 평가 실행

### 기본 실행

```bash
cd server

# 기본 평가 (K=5) - 타임스탬프로 저장
uv run python eval/r3/run_evaluation.py

# Top-K 변경
uv run python eval/r3/run_evaluation.py --top_k 10

# 결과 파일명 지정
uv run python eval/r3/run_evaluation.py --output 2024-01-15_embed_3-large
```

### 결과 파일명 컨벤션

**패턴**: `{날짜}_{변경요소}_{값}.json`

| 실험 목적          | 파일명 예시                                                        |
| ------------------ | ------------------------------------------------------------------ |
| 기준선 (현재 설정) | `2024-01-15_baseline.json`                                         |
| 임베딩 모델 비교   | `2024-01-15_embed_3-small.json`, `2024-01-15_embed_3-large.json`   |
| Top-K 비교         | `2024-01-15_topk_5.json`, `2024-01-15_topk_10.json`                |
| 청킹 전략 비교     | `2024-01-15_chunk_paragraph.json`, `2024-01-15_chunk_article.json` |
| 재랭커 추가        | `2024-01-15_rerank_cohere.json`, `2024-01-15_rerank_none.json`     |

**실행 예시**:

```bash
# 기준선
uv run python eval/r3/run_evaluation.py --output 2024-01-15_baseline

# 임베딩 모델 비교
uv run python eval/r3/run_evaluation.py --output 2024-01-15_embed_3-small
uv run python eval/r3/run_evaluation.py --output 2024-01-15_embed_3-large

# Top-K 비교
uv run python eval/r3/run_evaluation.py --top_k 5 --output 2024-01-15_topk_5
uv run python eval/r3/run_evaluation.py --top_k 10 --output 2024-01-15_topk_10
```

### 출력 예시

```text
============================================================
R3 법령 RAG 평가 시작
============================================================

평가셋: 30개 항목
Top-K: 5

평가 진행 중...

  [ 1/30] ✓ R3-0001 | MH-Recall: 1.00 | Recall: 0.50 | MRR: 1.00 | Latency: 360ms
  [ 2/30] ✓ R3-0002 | MH-Recall: 1.00 | Recall: 1.00 | MRR: 0.50 | Latency: 109ms
  ...

============================================================
평가 결과 요약
============================================================

📊 Retrieval 지표 (K=5):
  - Must-Have Recall@5: 0.4333
  - Recall@5:           0.3389
  - MRR:                0.4861

⏱️  Latency:
  - P50: 128.1ms
  - P95: 359.5ms

💾 결과 저장: eval/r3/results/2024-01-15_183826.json
```

## 평가 지표

### 현재 구현된 지표 (1단계)

| 지표                   | 설명                             | 중요도 |
| ---------------------- | -------------------------------- | ------ |
| **Must-Have Recall@K** | 핵심 조항(must_have=true) 검색률 | ⭐⭐⭐ |
| **Recall@K**           | 전체 gold_citations 검색률       | ⭐⭐⭐ |
| **MRR**                | 첫 번째 정답의 역순위            | ⭐⭐   |
| **Latency P50**        | 검색 응답 시간 중앙값            | ⭐⭐   |

### 향후 확장 예정 (2단계)

| 지표               | 설명                     | 구현 복잡도     |
| ------------------ | ------------------------ | --------------- |
| Negative Exclusion | 오답 조항 배제 능력      | 쉬움            |
| nDCG               | 그레이디드 랭킹 품질     | 중간            |
| Groundedness       | 답변이 컨텍스트 기반인지 | 복잡 (LLM 필요) |
| Faithfulness       | 환각 방지 정도           | 복잡 (LLM 필요) |

## 평가셋 구조

### 기본 구조

```json
{
  "version": "3.0",
  "description": "R3 도메인별 규제/법령 RAG 평가셋",
  "total_count": 30,
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
| `gold_citations[].must_have` | 핵심 근거 여부               | Must-Have Recall 측정     |
| `negatives`                  | 오답 근거 청크들             | 재랭킹/정확도 평가        |
| `expected_answer_bullets`    | 예상 답변 포인트             | Generation 평가           |
| `must_include`               | 답변에 포함되어야 할 키워드  | 답변 품질 평가            |
| `must_not_include`           | 답변에 포함되면 안 되는 내용 | 환각 방지 평가            |
| `notes`                      | 평가 의도/맥락               | 디버깅/분석용             |

## 평가 결과 구조

```json
{
  "timestamp": "2024-01-15T18:38:26.544001",
  "config": {
    "top_k": 5,
    "embedding_model": "text-embedding-3-small",
    "collection": "rag_laws",
    "num_items": 30
  },
  "summary": {
    "must_have_recall_at_k": 0.4333,
    "recall_at_k": 0.3389,
    "mrr": 0.4861,
    "latency_p50_ms": 128.1,
    "latency_p95_ms": 359.5
  },
  "details": [
    {
      "id": "R3-0001",
      "domain": "finance",
      "question": "...",
      "gold_ids": ["전자금융거래법|9|①", ...],
      "retrieved_ids": ["전자금융거래법|9|②|금융회사...", ...],
      "recall_at_k": 0.5,
      "must_have_recall_at_k": 1.0,
      "mrr": 1.0,
      "latency_ms": 360.0
    }
  ]
}
```

## 매칭 로직

### 기본 매칭 규칙

```python
def match_ids(retrieved_id: dict, gold_id: dict) -> bool:
    """두 ID가 매칭되는지 확인

    매칭 규칙:
    1. base_id (law_name, article_no, paragraph_no) 필수 일치
    2. gold_id에 article_title이 있으면 추가로 일치해야 함
    """
    if retrieved_id["base_id"] != gold_id["base_id"]:
        return False

    # gold에 article_title이 있으면 검증
    if gold_id["article_title"]:
        return retrieved_id["article_title"] == gold_id["article_title"]

    return True
```

### 산업융합촉진법 제10조 주의사항

같은 조에 여러 조항이 있는 경우 `article_title`로 구분 필요:

```json
// 규제 신속확인
{"law_name": "산업융합 촉진법", "article_no": "10", "article_title": "규제 신속확인"}

// 실증을 위한 규제특례
{"law_name": "산업융합 촉진법", "article_no": "10", "article_title": "실증을 위한 규제특례"}

// 임시허가
{"law_name": "산업융합 촉진법", "article_no": "10", "article_title": "임시허가"}
```

## 청킹 데이터

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

### 청킹 데이터 생성

청크 JSON은 평가셋 작성/검증용으로 필요할 때만 생성합니다.
`--export-chunks` 플래그를 사용하면 Vector DB 저장과 함께 청크 JSON도 생성됩니다.

```bash
cd server

# Vector DB만 생성 (기본)
uv run python scripts/collect_laws.py
uv run python scripts/collect_cases.py
uv run python scripts/collect_regulations.py

# Vector DB + 청크 JSON 함께 생성 (평가셋 작성용)
uv run python scripts/collect_laws.py --export-chunks        # → data/r3_data/chunks.json
uv run python scripts/collect_cases.py --export-chunks       # → data/r2_data/chunks.json
uv run python scripts/collect_regulations.py --export-chunks # → data/r1_data/chunks.json
```

**언제 `--export-chunks`를 사용하나요?**

- 평가셋을 새로 작성하거나 검증할 때
- 청킹 전략을 변경하고 chunks.json을 갱신할 때

**언제 사용하지 않아도 되나요?**

- 임베딩 모델만 변경해서 Vector DB를 다시 만들 때 (기존 chunks.json 그대로 사용)
- 일반적인 Vector DB 재생성 시

공통 유틸리티: `app/db/export.py`의 `save_chunks_json()` 함수 사용

## 평가 시나리오

### 1. 청킹 전략 비교

```bash
# 1. 다른 청킹 전략으로 데이터 수집
uv run python scripts/collect_laws.py --strategy semantic

# 2. 평가 실행
uv run python eval/r3/run_evaluation.py --output semantic-chunking
```

### 2. 임베딩 모델 비교

```bash
# .env에서 LLM_EMBEDDING_MODEL 변경 후

# 1. 데이터 재수집
uv run python scripts/collect_laws.py

# 2. 평가 실행
uv run python eval/r3/run_evaluation.py --output embedding-3-large
```

### 3. Top-K 값 비교

```bash
uv run python eval/r3/run_evaluation.py --top_k 3 --output k3
uv run python eval/r3/run_evaluation.py --top_k 5 --output k5
uv run python eval/r3/run_evaluation.py --top_k 10 --output k10
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

| 파일             | 경로                                      | 설명                                        |
| ---------------- | ----------------------------------------- | ------------------------------------------- |
| 공통 지표        | `server/eval/metrics.py`                  | Recall, MRR 등 계산 함수                    |
| R3 평가셋        | `server/eval/r3/evaluation_set.json`      | R3 RAG 평가셋 (30개)                        |
| R3 평가 스크립트 | `server/eval/r3/run_evaluation.py`        | R3 평가 실행                                |
| R3 평가 결과     | `server/eval/r3/results/`                 | 평가 결과 JSON                              |
| 청크 데이터      | `server/data/{r1,r2,r3}_data/chunks.json` | 청킹 결과 (gitignore)                       |
| 공통 유틸        | `server/app/db/export.py`                 | 청크 JSON 저장 함수                         |
| R3 수집          | `server/scripts/collect_laws.py`          | 법령 수집 (--export-chunks로 청크 저장)     |
| R2 수집          | `server/scripts/collect_cases.py`         | 승인사례 수집 (--export-chunks로 청크 저장) |
| R1 수집          | `server/scripts/collect_regulations.py`   | 규제제도 수집 (--export-chunks로 청크 저장) |
