# Server (Backend)

## Tech Stack

- **Framework**: FastAPI
- **Package**: uv (Python 3.12)
- **AI**: LangGraph, LangChain, OpenAI GPT-4o-mini
- **VectorDB**: ChromaDB
- **Integrations**: Notion API
- **Libraries**: Pydantic, yt-dlp, Whisper

## Repository Structure

```text
server/
├── .venv/                      # 가상환경
├── app/
│   ├── agents/                 # LangGraph AI Agent
│   │   ├── agents1/            # Agent
│   │   │   ├── graph.py
│   │   │   ├── tools.py
│   │   │   └── prompts.py
│   │   └── agents2/            # Agent
│   │       └── ...
│   ├── api/
│   │   ├── routes/             # API 엔드포인트
│   │   └── schemas/            # API Pydantic 스키마
│   ├── services/               # 비즈니스 로직
│   └── core/                   # 설정 관리
├── main.py                     # FastAPI 앱 생성, 라우터 등록
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

## Quickstart

### Install

```bash
cd server
uv sync
```

### Environment Variables

`.env` 설정

```env
OPENAI_API_KEY="sk-.."
```

## Run

### API Server (FastAPI)

```bash
uv run uvicorn app.main:app --reload
```

**API check:**

```bash
curl -X POST "http://127.0.0.1:8000/sample/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"hello"}'
```

**Swagger UI:**

```
http://127.0.0.1:8000/docs
```
