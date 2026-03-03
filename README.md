# SandboxIA

규제 샌드박스 신청 컨설팅을 지원하는 AI 멀티에이전트 시스템

## Overview

SandboxIA는 규제 샌드박스 신청 과정을 자동화하는 AI 기반 컨설팅 지원 시스템입니다. LangGraph 기반 멀티에이전트 아키텍처로 서비스 분석부터 신청서 작성까지 전 과정을 지원합니다.

### 핵심 기능

| 단계 | 기능 | 설명 |
|------|------|------|
| Step 1 | 서비스 구조화 | HWP 파일 파싱, 서비스 정보 추출 및 정규화 |
| Step 2 | 대상성 판단 | 규제 샌드박스 적용 대상 여부 판단 |
| Step 3 | 트랙 추천 | 신속확인/실증특례/임시허가 중 최적 트랙 추천 |
| Step 4 | 신청서 초안 | 트랙별 신청서 양식 자동 작성 |
| Step 5 | 전략 추천 | 유사 승인 사례 기반 전략 조언 (예정) |
| Step 6 | 리스크 체크 | QA 체크리스트 및 리스크 식별 (예정) |

## Tech Stack

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 16, React 19, TypeScript 5, TailwindCSS 4, TanStack Query 5, Zustand |
| Backend | FastAPI, LangGraph, LangChain, Pydantic |
| AI/ML | OpenAI GPT-4o, ChromaDB (Vector DB), RAGAS (RAG 평가) |
| Database | Supabase (PostgreSQL + Storage + Auth) |
| Infra | Vercel (Frontend), Docker (Backend) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client (Next.js 16)                         │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ React 19 │ TanStack Query │ Zustand │ React Hook Form │ Zod    ││
│  └─────────────────────────────────────────────────────────────────┘│
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST API + SSE (Progress Streaming)
┌────────────────────────────────▼────────────────────────────────────┐
│                      Server (FastAPI + LangGraph)                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      LangGraph Agents                          │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │ │
│  │  │ 1.Structurer │ │2.Eligibility │ │3.Recommender │           │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘           │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │ │
│  │  │  4.Drafter   │ │ 5.Advisor    │ │ 6.Checker    │           │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘           │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                              │                                       │
│  ┌───────────────────────────▼────────────────────────────────────┐ │
│  │                    Shared RAG Tools                             │ │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │ │
│  │  │ R1: 규제제도     │ │ R2: 승인사례    │ │ R3: 도메인법령   │   │ │
│  │  │ (트랙/절차/요건) │ │ (사례/조건)     │ │ (법령/인허가)   │   │ │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────┐
│                           External Services                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │
│  │   Supabase   │ │   ChromaDB   │ │  OpenAI API  │                 │
│  │  (DB/Auth)   │ │  (VectorDB)  │ │  (LLM/Embed) │                 │
│  └──────────────┘ └──────────────┘ └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.12+
- pnpm
- uv (Python package manager)
- Docker (ChromaDB용, 선택)

### Quick Start

```bash
# 1. 저장소 클론
git clone https://github.com/KernelAcademy-AICamp/2nd-pj-SandboxIA.git
cd 2nd-pj-SandboxIA

# 2. 환경 변수 설정
cp server/.env.example server/.env
cp client/.env.example client/.env.local
# .env 파일 편집하여 API 키 설정

# 3. 서버 실행 (터미널 1)
cd server
uv sync
uv run python scripts/collect_regulations.py  # RAG 데이터 구축
uv run uvicorn app.main:app --reload

# 4. 클라이언트 실행 (터미널 2)
cd client
pnpm install
pnpm run dev
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

자세한 설정은 각 디렉토리의 README를 참고하세요:
- [client/README.md](./client/README.md) - 프론트엔드 설정
- [server/README.md](./server/README.md) - 백엔드 설정

## Repository Structure

```
.
├── client/                    # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/              # App Router 페이지
│   │   ├── components/       # React 컴포넌트
│   │   ├── hooks/            # TanStack Query 훅
│   │   ├── lib/              # API 클라이언트, 유틸리티
│   │   ├── stores/           # Zustand 스토어
│   │   └── types/            # TypeScript 타입
│   └── README.md
│
├── server/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── agents/           # LangGraph 멀티에이전트
│   │   ├── api/              # API 라우트 & 스키마
│   │   ├── services/         # 비즈니스 로직
│   │   ├── tools/shared/     # 공용 RAG Tools
│   │   ├── core/             # 설정, LLM
│   │   └── db/               # Vector DB
│   ├── eval/                 # RAG 평가 시스템
│   └── README.md
│
├── doc/                       # 프로젝트 문서
├── CLAUDE.md                  # Claude Code 지침
└── README.md
```

## RAG System

3개의 도메인별 RAG 시스템으로 컨텍스트 기반 응답 생성:

| RAG | 데이터 소스 | 주요 활용 |
|-----|-------------|----------|
| R1 | 규제제도 정의, 트랙별 절차/요건/심사기준 | 대상성 판단, 트랙 추천, 신청서 작성 |
| R2 | 승인/반려 사례, 조건, 실증 범위 | 유사 사례 검색, 전략 조언 |
| R3 | 도메인별 법령 (의료법, 전자금융거래법 등) | 규제 쟁점 분석, 법적 근거 |

### RAG 평가

RAGAS 기반 평가 시스템으로 RAG 품질 측정:

```bash
cd server

# Retrieval 평가
uv run python eval/r3/run_evaluation.py --top_k 5

# LLM-as-Judge 평가
uv run python eval/r3/run_llm_evaluation.py --limit 5
```

## Branch Strategy

| 브랜치 | 용도 |
|--------|------|
| `main` | 프로덕션 배포 |
| `dev` | 개발 통합 |
| `feature/agent-*` | 에이전트 개발 |
| `feature/func-*` | 기능 개발 |
| `feature/uiux` | UI/UX 개발 |
| `eval/rag-*` | RAG 평가 실험 |

### PR 워크플로우

```bash
# 1. feature 브랜치에서 작업
git checkout -b feature/my-feature

# 2. 작업 완료 후 push
git add .
git commit -m "feat: 새 기능 추가"
git push origin feature/my-feature

# 3. GitHub에서 PR 생성 (base: dev)
```

## Development Tools

### CodeRabbit

PR 생성 시 자동 코드 리뷰. 설정: `.coderabbit.yaml`

### Claude Code (Optional)

AI 기반 개발 지원. 프로젝트 지침: `CLAUDE.md`

**권장 MCP 서버:**
- [context7](https://github.com/upstash/context7) - 라이브러리 문서 검색
- [supabase-mcp](https://github.com/supabase-community/supabase-mcp) - DB 스키마 관리

## Contributing

1. 이슈 생성 또는 할당된 이슈 확인
2. `dev`에서 feature 브랜치 생성
3. 작업 완료 후 PR 생성 (base: `dev`)
4. CodeRabbit 리뷰 확인 및 수정
5. 리뷰 승인 후 Merge

## Team

AI Camp 4th - Team SandboxIA
