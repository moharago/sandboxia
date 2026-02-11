# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SandboxIA is an AI-powered regulatory sandbox consultation support system. The application uses a multi-agent architecture to assist consultants with service description analysis, eligibility evaluation, track recommendation, and application draft generation.

## Architecture

```
Client (Next.js 16)                Server (FastAPI)
   Port 3000                          Port 8000
┌─────────────────────┐          ┌──────────────────┐
│  React 19           │          │  LangGraph       │
│  App Router         │←────────→│  Multi-Agent     │
│  TailwindCSS 4      │  REST    │  Supervisor      │
│  TanStack Query 5   │          │                  │
│  TypeScript         │          │  OpenAI/Tavily   │
└─────────────────────┘          └──────────────────┘
```

## Development Commands

### Client (`/client`)
```bash
pnpm install          # Install dependencies
pnpm run dev          # Dev server at http://localhost:3000
pnpm run build        # Production build
pnpm run lint         # ESLint
```

### Server (`/server`)
```bash
uv sync                                    # Install dependencies
uv run uvicorn app.main:app --reload       # Dev server at http://127.0.0.1:8000
```

API documentation: http://127.0.0.1:8000/docs

## Environment Variables

### Client (`.env.local`)
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Server (`.env`)
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Agent Architecture (LangGraph)

The server uses a **Supervisor Pattern** with 6 specialized agents:

### 1. Service Structurer Agent (`service_structurer/`)
Parses application forms and structures business service descriptions.
- **Tools**: Template Parser, Form Schema Generator, Auto-Fill, Patch, Canonical Converter, Uncertainty Detector

### 2. Eligibility Evaluator Agent (`eligibility_evaluator/`)
Determines regulatory sandbox eligibility.
- **Tools**: Rule Screener, Similar Case RAG, Decision Composer, Counter-example Generator

### 3. Track Recommender Agent (`track_recommender/`)
Recommends appropriate sandbox track (신속확인/실증특례/임시허가).
- **Tools**: Track Scorer, Track Definition RAG, Explainable Recommender, Preparation Checklist

### 4. Application Drafter Agent (`application_drafter/`)
Generates application document drafts.
- **Tools**: Template Selector, Section Mapper, Section Writer, Consistency Checker, Document Renderer

### 5. Strategy Advisor Agent (`strategy_advisor/`)
Provides strategic recommendations based on similar approved cases.
- **Tools**: Case Cluster Selector, Approval Pattern Extractor, Strategy Generator, Citation Snippet Provider

### 6. Risk Checker Agent (`risk_checker/`)
Performs QA checks and identifies risks from reviewer's perspective.
- **Tools**: Checklist Generator, Gap Detector, Risk Scenario Generator, Improvement Suggester, Final Report Generator

### Shared Tools (Cross-Agent)

**RAG Tools** - 모든 에이전트가 공용으로 사용:
| Tool | 데이터 | 주 사용처 |
|------|--------|----------|
| R1. 규제제도 & 절차 RAG | 트랙 정의, 절차, 요건, 심사 포인트 | 2, 3, 4, 6 |
| R2. 승인 사례 RAG | 승인/반려 사례, 조건, 실증 범위 | 2, 5, 6 |
| R3. 도메인별 규제·법령 RAG | 분야별 법령/인허가 체계 | 1, 2, 6 |

### Agent State Pattern
Agent state uses `TypedDict` with message accumulation. Recursion limit is set to 15 to prevent infinite loops.

### Adding New Agents
1. Create agent directory under `app/agents/`
2. Define `state.py` with TypedDict state
3. Define `tools.py` with `@tool` decorated functions
4. Define `nodes.py` with node functions
5. Define `graph.py` with StateGraph and edges
6. Register with supervisor's routing logic
7. Use shared RAG tools via `app/tools/shared/`

## API Patterns

### Backend (FastAPI)
- Routes in `app/api/routes/` with APIRouter
- Pydantic schemas in `app/api/schemas/`
- Business logic in `app/services/`

### Frontend (Next.js)
- Data fetching via TanStack Query hooks in `src/hooks/`
- API client functions in `src/lib/api.ts`
- Query keys format: `["resource", params]`

## Branch Strategy

- `main`: Production
- `dev`: Development
- `feature/agent-{name}`: Agent development
- `feature/func-{name}`: Feature development
- `feature/uiux`: Client UI development
- `feature/db-{name}`: Database schema & API development
- `eval/rag-{domain}`: RAG evaluation experiments (e.g., `eval/rag-domain-law`)

## MCP Servers

Claude Code에서 사용 가능한 MCP(Model Context Protocol) 서버:

### context7
라이브러리/프레임워크의 최신 공식 문서 검색.
- `resolve-library-id`: 라이브러리명 → Context7 ID 변환
- `query-docs`: 해당 라이브러리 문서에서 정보 검색
- **사용 예**: Next.js, LangGraph, TanStack Query 등의 최신 API 확인 시

### supabase
Supabase 프로젝트 관리 및 데이터베이스 작업.
- `list_tables`, `execute_sql`: 스키마 조회 및 쿼리 실행
- `apply_migration`: DDL 마이그레이션 적용
- `generate_typescript_types`: DB 스키마 기반 타입 생성
- `deploy_edge_function`: Edge Function 배포
- `get_logs`, `get_advisors`: 로그 조회 및 보안/성능 권고사항 확인
- **사용 예**: DB 스키마 변경, RLS 정책 설정, Edge Function 배포

### serena
시맨틱 코드 탐색 및 리팩토링 도구.
- `get_symbols_overview`: 파일 내 심볼(클래스, 함수 등) 개요
- `find_symbol`: 이름 패턴으로 심볼 검색
- `find_referencing_symbols`: 심볼 참조 위치 검색
- `replace_symbol_body`, `rename_symbol`: 코드 수정/리팩토링
- **사용 예**: 대규모 코드베이스에서 함수 추적, 안전한 리네이밍