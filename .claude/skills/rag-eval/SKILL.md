---
name: rag-eval
description: "RAG 평가 스크립트 실행. 자연어로 옵션을 지정하면 평가를 수행합니다. 트리거 - /rag-eval, /rag-eval --llm, RAG 평가 실행"
---

# RAG 평가 실행

사용자가 RAG 시스템 평가를 요청했습니다.

## 명령어 인자: $ARGUMENTS

---

## 실행 모드 판단

인자를 분석하여 실행 모드를 결정하세요:

### 모드 A: 단일 평가 (직접 실행)

단순한 단일 평가 요청일 때 Claude가 직접 실행합니다.

**패턴**: `/rag-eval`, `/rag-eval R3 top-k 10`, `/rag-eval --llm 5개만`

### 모드 B: 병렬 A/B 테스트 (서브에이전트)

여러 설정을 비교하는 요청일 때 서브에이전트를 병렬 호출합니다.

**패턴**: "top-k 5, 10, 15 비교", "k=5랑 k=10 비교해줘", "여러 설정으로 테스트"

→ Task tool로 `rag-evaluator` 에이전트를 **병렬 호출**
→ 각 설정별 서브에이전트 실행 후 결과 비교표 작성

### 모드 C: 전체 RAG 평가 (서브에이전트)

R1, R2, R3 전체 또는 다수를 평가하는 요청일 때 서브에이전트를 병렬 호출합니다.

**패턴**: "전체 RAG 평가", "R1, R2, R3 다 평가해줘", "모든 RAG"

→ Task tool로 `rag-evaluator` 에이전트를 **병렬 호출** (R1, R2, R3 각각)
→ 종합 리포트 작성

### 모드 D: 결과 분석 (서브에이전트)

기존 평가 결과를 분석하는 요청일 때 서브에이전트가 분석합니다.

**패턴**: "결과 분석", "이전 평가 비교", "baseline이랑 비교", "지난 결과들 분석"

→ Task tool로 `rag-evaluator` 에이전트 호출 (분석 모드)
→ 요약 리포트만 메인 컨텍스트로 전달

---

## 모드 A: 단일 평가 실행

### 1. 인자 파싱

`$ARGUMENTS`에서 다음 정보를 추출하세요:

| 추출 항목 | 자연어 예시                                                    | 값                      |
| --------- | -------------------------------------------------------------- | ----------------------- |
| 평가 유형 | `--llm` 포함 여부                                              | retrieval / llm         |
| RAG 타입  | "R1", "R2", "R3", "r1", "r2", "r3", "규제제도", "사례", "법령" | r1 / r2 / r3 (기본: r3) |
| strategy  | "strategy all", "전략 비교", "structured", "hybrid", "fulltext" | `--strategy {값}` (R2 전용) |
| top_k     | "top-k 10", "10개씩", "상위 10개"                              | `--top_k 10`            |
| output    | "~로 저장" (아래 파일명 생성 규칙 참조)                        | `--output {파일명}`     |
| limit     | "5개만 테스트", "3개로 제한"                                   | `--limit 5`             |
| trace     | "LangSmith 추적", "trace 켜줘", "추적해줘"                     | `--trace`               |

**R2 전용: strategy 매핑** (R2일 때만 적용):

| 자연어                                          | CLI 옵션               |
| ----------------------------------------------- | ---------------------- |
| "strategy all", "전략 비교", "전략 전부"        | `--strategy all`       |
| "structured", "구조화", "baseline"              | `--strategy structured`|
| "hybrid", "하이브리드", "fallback"              | `--strategy hybrid`    |
| "fulltext", "풀텍스트", "전문"                  | `--strategy fulltext`  |

**RAG 타입 매핑**:

- R1, 규제제도, 절차 → `r1`
- R2, 사례, 승인사례 → `r2`
- R3, 법령, 도메인 (또는 명시 없음) → `r3`

### 1-1. 파일명 생성 규칙 (output)

"~로 저장"이라고 말하면 **무조건 오늘 날짜를 앞에 붙여서** 파일명을 생성합니다.

**패턴**: `{YYYY-MM-DD}_{변경요소}_{변경값}` 또는 `{YYYY-MM-DD}_{이름}`

**변경요소 매핑**:

| 자연어                           | 변경요소   |
| -------------------------------- | ---------- |
| embedding, embed, 임베딩         | `embed`    |
| topk, top-k, top_k, k값          | `topk`     |
| chunk, chunking, 청킹, 청크      | `chunk`    |
| rerank, reranker, 재랭커, 재랭킹 | `rerank`   |
| strategy, 전략, 데이터전략       | `strategy` |

**변경값 매핑**:

| 자연어                            | 변경값       |
| --------------------------------- | ------------ |
| large, 3-large                    | `3-large`    |
| small, 3-small                    | `3-small`    |
| ada, ada-002                      | `ada-002`    |
| paragraph, 문단                   | `paragraph`  |
| article, 조문                     | `article`    |
| structured, 구조화                | `structured` |
| hybrid, 하이브리드                | `hybrid`     |
| fulltext, 풀텍스트                | `fulltext`   |
| all, 전체                         | `all`        |
| 프리셋 ID (C0~C6, E0~E3 등)       | 그대로       |
| 숫자 (5, 10, 15 등)               | 그대로       |

**예시 변환**:

| 자연어 입력              | 생성되는 파일명 (오늘 날짜: 2026-02-10) |
| ------------------------ | --------------------------------------- |
| "baseline으로 저장"      | `2026-02-10_baseline`                   |
| "embedding large로 저장" | `2026-02-10_embed_3-large`              |
| "embed small로 저장"     | `2026-02-10_embed_3-small`              |
| "topk 10으로 저장"       | `2026-02-10_topk_10`                    |
| "청킹 paragraph로 저장"  | `2026-02-10_chunk_paragraph`            |
| "청킹 C1으로 저장"       | `2026-02-10_chunk_C1`                   |
| "임베딩 E1으로 저장"     | `2026-02-10_embed_E1`                   |
| "rerank cohere로 저장"   | `2026-02-10_rerank_cohere`              |
| "전략 hybrid로 저장"     | `2026-02-10_strategy_hybrid`            |
| "전략 all로 저장"        | `2026-02-10_strategy_all`               |
| "v2로 저장"              | `2026-02-10_v2`                         |

**구현**: 오늘 날짜는 `date +%Y-%m-%d` 명령어로 얻거나 현재 날짜 사용

### 2. 스크립트 존재 확인

```bash
# Retrieval 평가 시
ls server/eval/{rag_type}/run_evaluation.py 2>/dev/null || echo "NOT_FOUND"

# LLM-as-Judge 평가 시
ls server/eval/{rag_type}/run_llm_evaluation.py 2>/dev/null || echo "NOT_FOUND"
```

### 3. 명령어 실행

```bash
cd server && uv run python eval/{rag_type}/run_{type}.py [옵션]
```

> 프로젝트 루트에서 `cd server`로 이동하여 실행. 절대 경로 하드코딩 금지.

### 4. 결과 보고

- 주요 지표 요약
- 결과 파일 저장 위치

---

## 모드 B/C/D: 서브에이전트 호출

Task tool을 사용하여 `rag-evaluator` 에이전트를 호출하세요.

### 병렬 A/B 테스트 예시 (모드 B)

```
사용자: "/rag-eval top-k 5, 10, 15 비교해줘"

→ Task tool 3개 병렬 호출:
  - prompt: "R3 retrieval 평가 실행. top_k=5, output=compare_k5"
  - prompt: "R3 retrieval 평가 실행. top_k=10, output=compare_k10"
  - prompt: "R3 retrieval 평가 실행. top_k=15, output=compare_k15"

→ 결과 비교표 작성
```

### 전체 RAG 평가 예시 (모드 C)

```
사용자: "/rag-eval 전체 RAG 평가해줘"

→ Task tool 3개 병렬 호출:
  - prompt: "R1 retrieval 평가 실행"
  - prompt: "R2 retrieval 평가 실행"
  - prompt: "R3 retrieval 평가 실행"

→ 종합 리포트 작성
```

### 결과 분석 예시 (모드 D)

```
사용자: "/rag-eval 최근 결과들 분석해줘"

→ Task tool 호출:
  - prompt: "server/eval/r3/results/ 디렉토리의 최근 평가 결과들을 읽고 비교 분석해줘. 지표 변화 추이, 개선/악화 항목을 정리해줘."

→ 분석 리포트 전달
```

### 변경요소별 비교 예시 (모드 D)

```
사용자: "/rag-eval embed 변경요소끼리 비교해줘"

→ Task tool 호출:
  - prompt: "server/eval/r3/results/ 디렉토리에서 파일명에 'embed'가 포함된 결과들을 찾아서 비교 분석해줘. 각 임베딩 모델별 성능 차이를 정리해줘."

→ 변경요소별 비교 리포트 전달
```

```
사용자: "/rag-eval topk 값별로 성능 비교"

→ Task tool 호출:
  - prompt: "server/eval/r3/results/ 디렉토리에서 파일명에 'topk'가 포함된 결과들을 찾아서 비교 분석해줘. Top-K 값에 따른 Recall/MRR 변화를 정리해줘."

→ 변경요소별 비교 리포트 전달
```

---

## 사용 예시

| 명령어                             | 모드 | 동작                                | 저장 파일명 예시             |
| ---------------------------------- | ---- | ----------------------------------- | ---------------------------- |
| `/rag-eval`                        | A    | R3 retrieval 직접 실행              | (타임스탬프)                 |
| `/rag-eval baseline으로 저장`      | A    | R3 retrieval + 파일명 지정          | `2026-02-10_baseline`        |
| `/rag-eval embedding large로 저장` | A    | R3 retrieval + 변경요소/값 파싱     | `2026-02-10_embed_3-large`   |
| `/rag-eval topk 10으로 저장`       | A    | R3 retrieval + 변경요소/값 파싱     | `2026-02-10_topk_10`         |
| `/rag-eval 청킹 C1으로 저장`       | A    | retrieval + 청킹 프리셋             | `2026-02-10_chunk_C1`        |
| `/rag-eval R1 임베딩 E1으로 저장`  | A    | R1 retrieval + 임베딩 프리셋        | `2026-02-10_embed_E1`        |
| `/rag-eval R2 전략 비교`           | A    | R2 retrieval + strategy all         | `2026-02-10_strategy_all`    |
| `/rag-eval R2 structured`          | A    | R2 retrieval + strategy structured  | (타임스탬프)                 |
| `/rag-eval R2 hybrid로 저장`       | A    | R2 retrieval + strategy hybrid      | `2026-02-10_strategy_hybrid` |
| `/rag-eval --llm R3 5개만`         | A    | R3 LLM 평가 직접 실행               | (타임스탬프)                 |
| `/rag-eval top-k 5, 10 비교`       | B    | 서브에이전트 2개 병렬 → 비교표      | -                            |
| `/rag-eval R1, R2, R3 전체`        | C    | 서브에이전트 3개 병렬 → 종합 리포트 | -                            |
| `/rag-eval 결과 분석`              | D    | 서브에이전트가 결과 파일 분석       | -                            |
| `/rag-eval embed끼리 비교`         | D    | 서브에이전트가 embed 변경요소 비교  | -                            |

## 주의사항

- **스크립트 확인 필수**: R1, R2는 미구현일 수 있음
- **LLM 평가 비용**: 처음 테스트 시 `--limit 3` 권장
- **병렬 실행**: 서브에이전트는 동시에 실행되어 시간 절약
- **컨텍스트 보호**: 대량 분석은 서브에이전트가 처리하여 메인 컨텍스트 보호
- **실험 프리셋**: 각 RAG는 `server/eval/{r1,r2,r3}/configs/`에서 프리셋 관리 (chunking.yaml, embedding.yaml, vectordb.yaml 등)

## 에이전트 레퍼런스

상세 옵션: `.claude/agents/rag-evaluator.md`

지금 바로 평가를 실행해주세요.
