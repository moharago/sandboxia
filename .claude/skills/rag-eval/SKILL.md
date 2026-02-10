---
name: rag-eval
description: "RAG 평가 스크립트 실행. 자연어로 옵션을 지정하면 평가를 수행합니다. 트리거 - /rag-eval, /rag-eval --llm, RAG 평가 실행"
---

# RAG 평가 실행

사용자가 RAG 시스템 평가를 요청했습니다.

## 명령어 인자: $ARGUMENTS

## 평가 유형 결정

- 인자에 `--llm`이 포함되어 있으면: **LLM-as-Judge 평가** (`run_llm_evaluation.py`)
- 그렇지 않으면: **Retrieval 평가** (`run_evaluation.py`)

## 작업 지시

### 1. 인자 파싱

`$ARGUMENTS`에서 다음 정보를 추출하세요:

| 추출 항목 | 자연어 예시                                                    | 값                      |
| --------- | -------------------------------------------------------------- | ----------------------- |
| 평가 유형 | `--llm` 포함 여부                                              | retrieval / llm         |
| RAG 타입  | "R1", "R2", "R3", "r1", "r2", "r3", "규제제도", "사례", "법령" | r1 / r2 / r3 (기본: r3) |
| top_k     | "top-k 10", "10개씩", "상위 10개"                              | `--top_k 10`            |
| output    | "baseline으로 저장", "v2로 저장"                               | `--output baseline`     |
| limit     | "5개만 테스트", "3개로 제한"                                   | `--limit 5`             |
| trace     | "LangSmith 추적", "trace 켜줘", "추적해줘"                     | `--trace`               |

**RAG 타입 매핑**:

- R1, 규제제도, 절차 → `r1`
- R2, 사례, 승인사례 → `r2`
- R3, 법령, 도메인 (또는 명시 없음) → `r3`

### 2. 스크립트 존재 확인

실행 전 반드시 확인 (평가 유형에 따라):

```bash
# Retrieval 평가 시
ls server/eval/{rag_type}/run_evaluation.py 2>/dev/null || echo "NOT_FOUND"

# LLM-as-Judge 평가 시
ls server/eval/{rag_type}/run_llm_evaluation.py 2>/dev/null || echo "NOT_FOUND"
```

스크립트가 없으면:

> "해당 RAG 타입의 평가 스크립트가 아직 구현되지 않았습니다. 현재 R3만 사용 가능합니다."

### 3. 명령어 실행

```bash
cd /Users/aistudy/Documents/ai-agent-kdt/2nd-pj-Sandbox/server && uv run python eval/{rag_type}/run_{type}.py [옵션]
```

### 4. 결과 보고

- 주요 지표 요약 (Recall, MRR, Faithfulness 등)
- 결과 파일 저장 위치

## 사용 예시

| 명령어                                       | RAG | 타입      | 옵션                           |
| -------------------------------------------- | --- | --------- | ------------------------------ |
| `/rag-eval`                                  | R3  | retrieval | (기본)                         |
| `/rag-eval --llm`                            | R3  | llm       | (기본)                         |
| `/rag-eval R1`                               | R1  | retrieval | (기본)                         |
| `/rag-eval --llm R2 5개만`                   | R2  | llm       | `--limit 5`                    |
| `/rag-eval R3 top-k 10 baseline으로`         | R3  | retrieval | `--top_k 10 --output baseline` |
| `/rag-eval --llm 법령 trace 켜고 3개 테스트` | R3  | llm       | `--trace --limit 3`            |

## 주의사항

- **스크립트 확인 필수**: R1, R2는 미구현일 수 있음
- **LLM 평가 비용**: 처음 테스트 시 `--limit 3` 권장
- **trace 요구사항**: `.env`에 `LANGCHAIN_API_KEY` 필요
- **평가 시간**: Retrieval ~수십 초, LLM ~수 분

## 에이전트 레퍼런스

상세 옵션 및 RAG별 지원 현황은 `.claude/agents/rag-evaluator.md` 참조

지금 바로 평가를 실행해주세요.
