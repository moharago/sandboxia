# Server (Backend)

## Tech Stack

- **Framework**: FastAPI
- **Package**: uv (Python 3.12)
- **AI**: LangGraph, LangChain, OpenAI GPT-4o-mini
- **VectorDB**: ChromaDB
- **Integrations**: 법령정보 API (law.go.kr)
- **Libraries**: Pydantic, httpx

## Repository Structure

```text
server/
├── app/
│   ├── agents/                 # LangGraph AI Agents
│   ├── api/
│   │   ├── routes/             # API 엔드포인트
│   │   └── schemas/            # Pydantic 스키마
│   ├── services/               # 비즈니스 로직
│   ├── tools/
│   │   └── shared/
│   │       └── rag/            # 공용 RAG Tools (R1, R2, R3)
│   ├── db/                     # DB 클라이언트
│   └── core/                   # 설정 관리
├── scripts/
│   └── collect_laws.py         # 법령 데이터 수집 스크립트
├── data/
│   └── chroma/                 # Vector DB 저장소 (gitignore)
├── test/                       # 테스트 파일
├── main.py
├── pyproject.toml
└── README.md
```

## 설치 가이드

### 1. 의존성 설치

```bash
cd server
uv sync
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Tavily (웹 검색)
TAVILY_API_KEY=tvly-...

# 법령 API (law.go.kr)
LAW_API_BASE_URL=https://www.law.go.kr
LAW_API_OC=dasolyou

# LLM 설정
LLM_MODEL=gpt-4o-mini
LLM_EMBEDDING_MODEL=text-embedding-3-small

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Vector DB 구축 (필수)

법령 데이터를 수집하여 Vector DB를 생성합니다.

```bash
uv run python scripts/collect_laws.py
```

수집 대상 법령:
- 의료법
- 전자금융거래법
- 데이터 산업진흥 및 이용촉진에 관한 기본법
- 신용정보의 이용 및 보호에 관한 법률
- 개인정보 보호법
- 전기통신사업법

> **Note**: Vector DB(`data/chroma/`)는 Git에 포함되지 않습니다. 코드를 pull 받은 후 반드시 이 스크립트를 실행하세요.

### 4. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

## API 확인

**Health Check:**

```bash
curl http://127.0.0.1:8000/
```

**Sample Query:**

```bash
curl -X POST "http://127.0.0.1:8000/sample/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"hello"}'
```

**Swagger UI:**

```
http://127.0.0.1:8000/docs
```

## 테스트

```bash
# RAG Tool 테스트
uv run python test/domain_law_rag.py
```

## 데이터 갱신

법령이 개정되었거나 Vector DB를 재구축해야 할 경우:

```bash
# 기존 데이터 삭제 후 재수집
rm -rf data/chroma
uv run python scripts/collect_laws.py
```
