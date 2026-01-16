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

The server uses a **Supervisor Pattern** where a central agent routes tasks to specialists:

- **Supervisor (`sample_supervisor/`)**: Routes queries to appropriate worker agents
- **Researcher (`sample_researcher/`)**: Web search via Tavily API
- **Calculator (`sample_calculator/`)**: Math operations and time queries

Agent state uses `TypedDict` with message accumulation. Recursion limit is set to 15 to prevent infinite loops.

### Adding New Agents
1. Create agent directory under `app/agents/`
2. Define `graph.py` with StateGraph and nodes
3. Implement `tools.py` with `@tool` decorated functions
4. Register with supervisor's routing logic

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
