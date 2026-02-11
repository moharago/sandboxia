[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/fNIvjsmp)

# SandboxIA

규제 샌드박스 신청 컨설팅을 지원하는 AI 멀티에이전트 시스템

## Overview

SandboxIA는 규제 샌드박스 신청 과정을 자동화하는 AI 기반 컨설팅 지원 시스템입니다.

**핵심 기능:**

- 서비스 구조화 및 대상성 판단
- 트랙 추천 (신속확인/실증특례/임시허가)
- 신청서 초안 자동 생성
- 전략 추천 및 리스크 체크

**기술 스택:**

- Frontend: Next.js 16, React 19, TailwindCSS 4, TanStack Query
- Backend: FastAPI, LangGraph (Multi-Agent)
- AI/ML: OpenAI GPT-4o, RAG (ChromaDB), RAGAS
- Infra: Supabase, Vercel

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Next.js)                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │ REST API
┌─────────────────────────────▼───────────────────────────────────┐
│                     Server (FastAPI + LangGraph)                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Supervisor Agent                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │
│  │  │Structurer│ │Eligibility│ │  Track   │ │  Draft   │ ...  │ │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │ │
│  └───────┼────────────┼────────────┼────────────┼─────────────┘ │
│          └────────────┴─────┬──────┴────────────┘               │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐   │
│  │                    Shared RAG Tools                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │ R1: 규제제도 │  │ R2: 승인사례 │  │ R3: 도메인법령│       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## RAG Evaluation System

RAG 시스템의 품질을 정량적으로 측정하고 개선하기 위한 평가 파이프라인을 구축했습니다.

### 평가 지표

| 카테고리       | 지표               | 설명                                  |
| -------------- | ------------------ | ------------------------------------- |
| **Retrieval**  | Must-Have Recall@K | 핵심 조항 검색률                      |
|                | Recall@K           | 전체 정답 검색률                      |
|                | MRR                | 첫 번째 정답의 역순위                 |
| **Generation** | Faithfulness       | 응답의 컨텍스트 기반 여부 (환각 방지) |
|                | Answer Relevancy   | 질문-응답 적합도                      |

### 평가 실행

```bash
cd server

# Retrieval 평가 (빠름, 비용 없음)
uv run python eval/r3/run_evaluation.py --top_k 5

# LLM-as-Judge 평가 (RAGAS 기반)
uv run python eval/r3/run_llm_evaluation.py --limit 5
```

### A/B 테스트 자동화

Claude Code의 서브에이전트를 활용한 병렬 평가 시스템:

```bash
# 단일 평가
/rag-eval R3 top-k 10

# 병렬 A/B 테스트 (서브에이전트)
/rag-eval top-k 5, 10, 15 비교해줘

# 변경요소별 비교 분석
/rag-eval embed끼리 비교해줘
```

**서브에이전트 활용:**

- 병렬 A/B 테스트: 여러 설정을 동시에 평가하여 시간 절약
- 결과 분석: 대량의 평가 결과를 분석하여 요약 리포트 생성
- 컨텍스트 보호: 분석 작업을 서브에이전트에 위임하여 메인 컨텍스트 유지

## Repository Structure

```
.
├── client/                 # Next.js 프론트엔드
│   └── README.md
├── server/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── agents/         # LangGraph 멀티에이전트
│   │   └── tools/shared/   # 공용 RAG Tools (R1, R2, R3)
│   ├── eval/               # RAG 평가 시스템
│   │   ├── metrics.py      # Retrieval 지표
│   │   ├── llm_metrics.py  # RAGAS 기반 LLM 지표
│   │   └── r3/             # R3 RAG 평가셋 & 스크립트
│   └── README.md
├── doc/                    # 프로젝트 문서
├── README.md
└── CLAUDE.md               # Claude Code 지침
```

## Getting Started

자세한 설정은 각 디렉토리의 README 문서 참고:

- [client/README.md](./client/README.md)
- [server/README.md](./server/README.md)

## Contributing

### 브랜치 전략

- `main`: 프로덕션
- `dev`: 개발
- `baseline`: 초기 프로젝트 세팅
- `feature/agent-{에이전트명}`: 에이전트 개발
- `feature/tool-{툴명}`: 툴 개발
- `feature/func-{기능명}`: 기능 개발
- `feature/uiux`: client 화면 개발
- `feature/db-{name}`: Database schema & API development
- `eval/rag-{domain}`: RAG 평가 실험 (예: `eval/rag-domain-law`)

### PR 워크플로우

**PR 방향:**

| From                    | To     | 설명              |
| ----------------------- | ------ | ----------------- |
| `feature/*`, `fix/*` 등 | `dev`  | 기능 개발 완료 시 |
| `dev`                   | `main` | 배포 시           |

**올바른 PR 생성 방법:**

```bash
# 1. 내 작업 브랜치에서 작업 완료 후 커밋
git checkout feature/my-feature
git add .
git commit -m "feat: 새 기능 추가"

# 2. 내 브랜치를 원격에 push
git push origin feature/my-feature

# 3. GitHub 웹사이트에서 PR 생성
#    - base 브랜치를 dev (또는 main)로 설정
#    - compare 브랜치를 내 작업 브랜치로 설정
```

> **주의:** dev나 main으로 checkout해서 pull/merge 하지 마세요!
> PR은 GitHub 웹에서 생성하고, 리뷰 후 "Merge" 버튼으로 머지합니다.

### CodeRabbit (AI 코드 리뷰)

이 프로젝트는 [CodeRabbit](https://coderabbit.ai)을 사용하여 자동 코드 리뷰를 수행합니다.

**동작 방식:**

1. `dev` 또는 `main` 브랜치로 PR 생성
2. CodeRabbit이 자동으로 코드 분석 및 리뷰 코멘트 작성
3. 리뷰 내용 확인 후 필요시 코드 수정
4. 리뷰 완료 후 "Merge pull request" 버튼 클릭

**설정 파일:** `.coderabbit.yaml`

### Claude Code & MCP (Optional)

[Claude Code](https://claude.ai/code)를 사용하면 AI 기반 개발 지원을 받을 수 있습니다. 추가로 MCP(Model Context Protocol) 서버를 연결하면 더 풍부한 컨텍스트와 도구를 활용할 수 있습니다.

> **필수 사항은 아닙니다.** MCP 없이도 개발에 전혀 문제가 없으며, 필요에 따라 선택적으로 활용하세요.

**권장 MCP 서버:**

| 서버                                                           | 용도                      | 활용 예시                   |
| -------------------------------------------------------------- | ------------------------- | --------------------------- |
| [context7](https://github.com/upstash/context7)                | 라이브러리 최신 문서 검색 | Next.js, LangGraph API 확인 |
| [supabase](https://github.com/supabase-community/supabase-mcp) | DB 스키마 관리 & 쿼리     | 마이그레이션, 타입 생성     |
| [serena](https://github.com/oraios/serena)                     | 시맨틱 코드 탐색          | 심볼 검색, 리팩토링         |

**설정 방법:**

1. Claude Code 설치 후 `.mcp.json` 파일 생성
2. 각 MCP 서버의 공식 문서를 참고하여 설정
3. 프로젝트별 지침은 `CLAUDE.md` 참고

## 👥 Team

AI Camp 4th - Team SandboxIA
