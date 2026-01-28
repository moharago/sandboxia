# Server (Backend)

## Tech Stack

- **Framework**: FastAPI
- **Package**: uv (Python 3.12)
- **AI**: LangGraph, LangChain, OpenAI GPT-4o-mini
- **VectorDB**: ChromaDB
- **Database**: Supabase (PostgreSQL)
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

# Google Drive (RAG 데이터)
GOOGLE_DRIVE_URL=https://drive.google.com/drive/folders/
R1_DATA_ID=your-folder-id

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key

```

### Supabase 설정

1. [Supabase](https://supabase.com)에서 프로젝트 생성
2. Project Settings > API에서 URL과 service_role key 복사
3. `.env`에 `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` 설정

### 3. Vector DB 구축 (필수)

RAG 데이터를 수집하여 Vector DB를 생성합니다.

```bash
# R1: 규제제도 데이터 (Google Drive에서 다운로드)
uv run python scripts/collect_regulations.py

# R3: 법령 데이터 (법령 API에서 수집)
uv run python scripts/collect_laws.py
```

**R1 수집 대상 (규제제도):**
- ICT 규제샌드박스 제도 정의, 절차, 요건, 심사기준

**R3 수집 대상 (법령):**
- 의료법
- 전자금융거래법
- 데이터 산업진흥 및 이용촉진에 관한 기본법
- 신용정보의 이용 및 보호에 관한 법률
- 개인정보 보호법
- 전기통신사업법
- 정보통신 진흥 및 융합 활성화 등에 관한 특별법

> **Note**: Vector DB(`data/chroma/`)는 Git에 포함되지 않습니다. 코드를 pull 받은 후 반드시 스크립트를 실행하세요.

### 4. 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

## API 확인

**Health Check:**

```bash
curl http://127.0.0.1:8000/
```

**Swagger UI:**

```
http://127.0.0.1:8000/docs
```

## 테스트

```bash
# R1 규제제도 RAG 테스트
uv run python test/regulation_rag.py

# R3 법령 RAG 테스트
uv run python test/domain_law_rag.py
```

## 데이터 갱신

데이터가 변경되었거나 Vector DB를 재구축해야 할 경우:

```bash
# 기존 데이터 삭제 후 재수집
rm -rf data/chroma

# R1: 규제제도 데이터
uv run python scripts/collect_regulations.py

# R3: 법령 데이터
uv run python scripts/collect_laws.py
```
