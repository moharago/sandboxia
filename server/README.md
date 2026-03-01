# Server (Backend)

규제 샌드박스 컨설팅 시스템의 FastAPI + LangGraph 백엔드

## Tech Stack

| 영역 | 기술 |
|------|------|
| Framework | FastAPI, Uvicorn |
| AI Agent | LangGraph, LangChain |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Vector DB | ChromaDB |
| Database | Supabase (PostgreSQL) |
| Storage | Supabase Storage |
| Auth | Supabase Auth (JWT) |
| Package | uv (Python 3.12) |

## Getting Started

### Prerequisites

- Python 3.12+
- uv (Python package manager)
- Docker (ChromaDB 서버용, 선택)
- LibreOffice (PDF 변환용)

### Installation

```bash
cd server
uv sync
```

### Environment Variables

`.env` 파일 생성:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Tavily (웹 검색, 선택)
TAVILY_API_KEY=tvly-...

# Upstage (대체 임베딩, 선택)
UPSTAGE_API_KEY=up_...

# 법령 API (law.go.kr)
LAW_API_BASE_URL=https://www.law.go.kr
LAW_API_OC=your-api-key

# LLM 설정
LLM_MODEL=gpt-4o-mini
LLM_EMBEDDING_MODEL=text-embedding-3-large

# ChromaDB
CHROMA_MODE=persistent           # persistent | http | ephemeral
CHROMA_HOST=localhost            # http 모드용
CHROMA_PORT=8000                 # http 모드용
CHROMA_PERSIST_DIR=./data/chroma # persistent 모드용

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

# Google Drive (RAG 데이터)
R1_DATA_ID=your-folder-id
R2_DATA_ID=your-folder-id

# 문서 템플릿 (DOCX)
DRAFT_TEMPLATE_FASTCHECK_ID=your-file-id
DRAFT_TEMPLATE_TEMPORARY_ID=your-file-id
DRAFT_TEMPLATE_DEMONSTRATION_ID=your-file-id
```

### Vector DB Setup

RAG 데이터 수집 및 Vector DB 구축:

```bash
# R1: 규제제도 데이터 (Google Drive)
uv run python scripts/collect_regulations.py

# R3: 법령 데이터 (법령 API)
uv run python scripts/collect_laws.py
```

**R1 데이터 (규제제도):**
- ICT 규제샌드박스 트랙별 정의, 절차, 요건, 심사기준

**R2 데이터 (승인사례):**
- 승인/반려 사례, 조건, 실증 범위 (JSON 형태)

**R3 데이터 (법령):**
- 의료법, 전자금융거래법, 개인정보보호법 등

### Run Server

```bash
uv run uvicorn app.main:app --reload
```

**Endpoints:**
- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

## Project Structure

```
server/
├── app/
│   ├── main.py                       # FastAPI app entry
│   │
│   ├── agents/                       # LangGraph AI Agents
│   │   ├── service_structurer/       # Step 1: HWP → Canonical
│   │   │   ├── state.py              # TypedDict state
│   │   │   ├── graph.py              # StateGraph definition
│   │   │   ├── nodes.py              # Node functions
│   │   │   └── prompts.py            # LLM prompts
│   │   ├── eligibility_evaluator/    # Step 2: Eligibility check
│   │   │   ├── state.py
│   │   │   ├── graph.py
│   │   │   ├── nodes.py
│   │   │   └── tools.py              # rule_screener tool
│   │   ├── track_recommender/        # Step 3: Track recommendation
│   │   │   ├── state.py
│   │   │   ├── graph.py
│   │   │   └── nodes.py
│   │   ├── application_drafter/      # Step 4: Draft generation
│   │   │   ├── state.py
│   │   │   ├── graph.py
│   │   │   └── nodes.py
│   │   └── utils/                    # Agent utilities
│   │       ├── streaming.py          # Progress tracking wrapper
│   │       └── ...
│   │
│   ├── api/
│   │   ├── routes/                   # API endpoints
│   │   │   ├── agents.py             # Agent execution endpoints
│   │   │   ├── agent_progress.py     # SSE progress streaming
│   │   │   ├── documents.py          # DOCX/PDF generation
│   │   │   ├── files.py              # File download
│   │   │   └── users.py              # User management
│   │   ├── schemas/                  # Pydantic request/response
│   │   └── deps.py                   # Dependencies (auth)
│   │
│   ├── services/                     # Business logic
│   │   ├── structure_service.py
│   │   ├── eligibility_service.py
│   │   ├── track_service.py
│   │   ├── draft_service.py
│   │   ├── project_service.py
│   │   ├── document_generator.py     # DOCX/PDF generation
│   │   └── parsers/
│   │       └── hwp_parser.py         # HWP file parsing
│   │
│   ├── tools/
│   │   └── shared/
│   │       └── rag/                  # Shared RAG tools
│   │           ├── regulation_rag.py # R1: 규제제도
│   │           ├── case_rag.py       # R2: 승인사례
│   │           └── domain_law_rag.py # R3: 도메인법령
│   │
│   ├── core/
│   │   ├── config.py                 # Settings, env vars
│   │   ├── llm.py                    # LLM instances
│   │   ├── constants.py              # Collection names, mappings
│   │   ├── progress_store.py         # SSE progress tracking
│   │   └── exceptions.py             # Custom exceptions
│   │
│   ├── db/
│   │   └── vector.py                 # ChromaDB client
│   │
│   ├── rag/
│   │   ├── config.py                 # Chunking/embedding configs
│   │   ├── chunkers/                 # Document chunkers
│   │   │   └── r3_law.py             # Law-specific chunker
│   │   └── collectors/               # Data collectors
│   │       └── r3_collector.py
│   │
│   └── data/
│       ├── form/                     # Form schemas (JSON)
│       │   ├── fastcheck.json
│       │   ├── temporary.json
│       │   ├── demonstration.json
│       │   └── counseling.json
│       └── canonical/                # Canonical structure schema
│           └── schema.json
│
├── eval/                             # RAG evaluation
│   ├── metrics.py                    # Retrieval metrics
│   ├── llm_metrics.py                # RAGAS-based metrics
│   └── r3/
│       ├── configs/                  # Chunking/embedding presets
│       ├── evalset.json              # Evaluation dataset
│       ├── run_evaluation.py         # Retrieval evaluation
│       └── run_llm_evaluation.py     # LLM evaluation
│
├── scripts/
│   ├── collect_regulations.py        # R1 data collection
│   └── collect_laws.py               # R3 data collection
│
├── test/                             # Tests
│   ├── regulation_rag.py
│   └── domain_law_rag.py
│
├── main.py                           # Entry point
├── pyproject.toml                    # Dependencies
├── docker-compose.yml                # ChromaDB + services
└── Dockerfile
```

## Agent Architecture

### LangGraph Workflow

각 에이전트는 `StateGraph` 패턴을 사용:

```python
class AgentState(TypedDict):
    """Agent state with message accumulation"""
    messages: Annotated[list, add_messages]
    # ... input fields
    # ... intermediate results
    # ... output fields

graph = StateGraph(AgentState)
graph.add_node("node_name", node_function)
graph.add_edge("node_a", "node_b")
graph.set_entry_point("start_node")
agent = graph.compile()
```

### Implemented Agents

| Agent | Workflow | RAG Tools |
|-------|----------|-----------|
| **1. Service Structurer** | `parse_hwp` → `build_structure` | - |
| **2. Eligibility Evaluator** | `screen` → `search_all_rag` → `compose_decision` → `generate_evidence` | R1, R2, R3 |
| **3. Track Recommender** | `retrieve_cases` → `score_all_tracks` → `retrieve_definitions` → `generate_recommendation` | R1, R2 |
| **4. Application Drafter** | `load_form_schema` → `retrieve_context` → `generate_draft` | R1, R2, R3 |

### Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Client Input (HWP + Form)                  │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Step 1: Service Structurer                       │
│              Output: canonical_structure                      │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Step 2: Eligibility Evaluator                    │
│              Output: eligibility_label, evidence              │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Step 3: Track Recommender                        │
│              Output: recommended_track, comparison            │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Step 4: Application Drafter                      │
│              Output: application_draft (form values)          │
└───────────────────────────┬──────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Document Generation (DOCX/PDF)                   │
└──────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agents/structure` | Step 1: Service structuring |
| POST | `/api/v1/agents/eligibility` | Step 2: Eligibility evaluation |
| PATCH | `/api/v1/agents/eligibility/{id}/final-decision` | Update final decision |
| POST | `/api/v1/agents/track` | Step 3: Track recommendation |
| GET | `/api/v1/agents/track/{id}` | Get cached track results |
| POST | `/api/v1/agents/draft` | Step 4: Draft generation |
| PATCH | `/api/v1/agents/draft/{id}` | Update draft card |

### Progress Streaming (SSE)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/agents/progress/nodes/{agent_type}` | Get agent node definitions |
| GET | `/api/v1/agents/progress/nodes` | Get all agents' nodes |
| GET | `/api/v1/agents/progress/subscribe/{project_id}` | SSE subscription |

### Document & Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/documents/download/{form_id}` | Download DOCX/PDF |
| GET | `/api/v1/files/download/{file_id}` | Download uploaded file |

### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| DELETE | `/api/users/me` | Delete user account |

## Shared RAG Tools

### R1: 규제제도 & 절차 RAG

```python
# app/tools/shared/rag/regulation_rag.py
async def search_regulations(query: str, top_k: int = 5) -> list[RegulationResult]:
    """트랙 정의, 절차, 요건, 심사기준 검색"""
```

### R2: 승인 사례 RAG

```python
# app/tools/shared/rag/case_rag.py
async def search_cases(query: str, top_k: int = 5) -> list[CaseResult]:
    """승인/반려 사례, 조건, 실증 범위 검색"""
```

### R3: 도메인별 법령 RAG

```python
# app/tools/shared/rag/domain_law_rag.py
async def search_laws(query: str, top_k: int = 5) -> list[LawResult]:
    """도메인별 규제/법령 검색"""
```

## Document Generation

### Template System

`docxtpl` + Jinja2 기반 DOCX 템플릿:

```python
# app/services/document_generator.py
def generate_document(form_id: str, form_values: dict) -> bytes:
    """DOCX 문서 생성"""
    template = load_template(form_id)
    context = build_context(form_values)
    return template.render(context)
```

### PDF Conversion

LibreOffice CLI 사용:

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
apt-get install libreoffice
```

## Authentication

Supabase Auth JWT 기반:

```python
# app/api/deps.py
async def get_auth_user(request: Request) -> AuthUser:
    """JWT 토큰 검증 및 사용자 정보 추출"""
    token = request.headers.get("Authorization")
    # Decode & validate JWT
```

## Progress Tracking

SSE 기반 실시간 진행 상태:

```python
# app/core/progress_store.py
progress_store.start(project_id, agent_type)
progress_store.update_node(project_id, node_name, "node_start")
progress_store.update_node(project_id, node_name, "node_end")
progress_store.end(project_id)
```

**Events:**
- `agent_start` - 에이전트 시작
- `node_start` - 노드 실행 시작
- `node_end` - 노드 실행 완료
- `agent_end` - 에이전트 완료
- `error` - 에러 발생

## RAG Evaluation

RAGAS 기반 평가 시스템:

```bash
# Retrieval 평가 (빠름, 비용 없음)
uv run python eval/r3/run_evaluation.py --top_k 5

# LLM-as-Judge 평가 (RAGAS)
uv run python eval/r3/run_llm_evaluation.py --limit 5
```

**평가 지표:**

| 카테고리 | 지표 | 설명 |
|----------|------|------|
| Retrieval | Must-Have Recall@K | 필수 조항 검색률 |
| | Recall@K | 전체 정답 검색률 |
| | MRR | 첫 번째 정답의 역순위 |
| Generation | Faithfulness | 컨텍스트 기반 여부 |
| | Answer Relevancy | 질문-응답 적합도 |

## Database Schema

### Supabase Tables

| Table | Description |
|-------|-------------|
| `projects` | 프로젝트 메타데이터 (canonical, results) |
| `project_files` | 업로드 파일 참조 |
| `users` | 사용자 프로필 |

### Vector DB Collections

| Collection | Description |
|------------|-------------|
| `rag_regulations` | R1: 규제제도 |
| `rag_cases` | R2: 승인사례 |
| `rag_laws` | R3: 도메인법령 |

## Scripts

| 명령어 | 설명 |
|--------|------|
| `uv run uvicorn app.main:app --reload` | 개발 서버 |
| `uv run python scripts/collect_regulations.py` | R1 데이터 수집 |
| `uv run python scripts/collect_laws.py` | R3 데이터 수집 |
| `uv run pytest` | 테스트 실행 |

## Docker

```bash
# ChromaDB 서버 실행
docker-compose up -d chroma

# 전체 서비스 실행
docker-compose up -d
```

## Data Refresh

Vector DB 재구축:

```bash
# 기존 데이터 삭제
rm -rf data/chroma

# 데이터 재수집
uv run python scripts/collect_regulations.py
uv run python scripts/collect_laws.py
```
