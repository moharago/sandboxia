# Server CLAUDE.md

FastAPI + LangGraph 기반 AI 에이전트 서버 개발 가이드.

## 프로젝트 구조

```
server/
├── app/
│   ├── agents/                 # LangGraph AI Agents
│   │   ├── supervisor/         # 중앙 라우팅 에이전트
│   │   ├── service_structurer/ # 1. 서비스 구조화
│   │   ├── eligibility_evaluator/ # 2. 대상성 판단
│   │   ├── track_recommender/  # 3. 트랙 추천
│   │   ├── application_drafter/ # 4. 신청서 초안
│   │   ├── strategy_advisor/   # 5. 전략 추천
│   │   └── risk_checker/       # 6. 리스크 체크
│   ├── tools/
│   │   ├── shared/             # 공용 Tool
│   │   │   └── rag/            # R1, R2, R3 RAG Tools
│   │   └── {agent}/            # 에이전트별 전용 Tool
│   ├── api/
│   │   ├── routes/             # API 엔드포인트
│   │   └── schemas/            # Pydantic 스키마
│   ├── services/               # 비즈니스 로직
│   ├── core/
│   │   ├── config.py           # 설정
│   │   └── exceptions.py       # 커스텀 예외
│   └── db/
│       └── vector.py           # Vector DB 클라이언트
├── main.py
└── pyproject.toml
```

## 에이전트별 Tool 사용 관계

### 1. Service Structurer (서비스 구조화)

**전용 Tools:**
- A. 신청서 템플릿/구조 파서
- B. UI Form Schema 생성
- C. 자동 채움(프리필)
- D. 사용자 수정 반영(Patch)
- F. 불확실/충돌 탐지 & 추가 질문 생성
- G. 규제 쟁점 후보 도출

**공용 RAG:** R3(도메인 법령), R1(제도 정의)

**출력:** Canonical 구조 → 2~6번 에이전트 입력

---

### 2. Eligibility Evaluator (대상성 판단)

**전용 Tools:**
- A. Rule 스크리너 (키워드/조건/신호)
- C. 판정 통합 (Decision Composer)
- D. 반례/주의사항 생성 (옵션)

**공용 RAG:** R2(유사 승인사례), R1(제도/절차), R3(법령/인허가)

---

### 3. Track Recommender (트랙 추천)

**전용 Tools:**
- A. 트랙 적합도 스코어링
- C. 설명 생성 (고객사 설명용 템플릿)
- D. 트랙별 준비 항목 도출 (옵션)

**공용 RAG:** R1(트랙 정의/요건), R2(사례 기반), R3(도메인 제약)

---

### 4. Application Drafter (신청서 초안)

**전용 Tools:**
- A. 양식 선택/버전 매칭
- B. 섹션별 컨텐츠 매핑
- C. 섹션 문장 생성
- D. 일관성/중복/형식 검수
- E. DOCX/PDF 렌더링

**공용 RAG:** R1(섹션 요구/작성 가이드), R2/R3(근거 문장)

**필드별 생성 원칙:** 

| 필드 유형 | canonical (입력) | draft (출력) |
|-----------|------------------|--------------|
| 서술형 설명 | 원본 그대로 | AI 다듬기 OK |
| 메타데이터 (expected_agency 등) | 원본 or null | 생성 금지 |
| 원본 없는 필드 (additional_questions 등) | null | AI 추론 + `generated_by: "ai"` |

---

### 5. Strategy Advisor (전략 추천)

**전용 Tools:**
- B. 승인 포인트 패턴 추출
- C. 이번 건 적용 전략 생성
- D. 인용 후보/표현 추천
- E. 유사 사례 없음 대응

**공용 RAG:** R2(핵심), R1/R3(보조)

---

### 6. Risk Checker (체크리스트 & 리스크)

**전용 Tools:**
- A. 기준 체크리스트 생성
- B. 누락/약점 탐지
- C. 리스크 시나리오 생성
- D. 개선 문장/대체 표현 생성
- E. 최종 검수 리포트 생성

**공용 RAG:** R1(요건/절차), R3(법령 리스크), R2(반려/보완 패턴)


---

## 공용 Tool 구현 위치

```
app/tools/shared/
└── rag/
    ├── __init__.py
    ├── regulation_rag.py       # R1: 규제제도 & 절차
    ├── case_rag.py             # R2: 승인 사례
    └── domain_law_rag.py       # R3: 도메인별 법령
```

## 개발 명령어

```bash
# 의존성 설치
uv sync

# 개발 서버 실행
uv run uvicorn app.main:app --reload

# 테스트 실행
uv run pytest

# 특정 에이전트 테스트
uv run pytest tests/test_agents/test_{agent_name}.py
```

## API 엔드포인트 패턴

```
POST /api/v1/agents/structure    # 1. 서비스 구조화
POST /api/v1/agents/eligibility  # 2. 대상성 판단
POST /api/v1/agents/track        # 3. 트랙 추천
POST /api/v1/agents/draft        # 4. 신청서 초안
POST /api/v1/agents/strategy     # 5. 전략 추천
POST /api/v1/agents/risk         # 6. 리스크 체크

POST /api/v1/agents/full-pipeline  # 전체 파이프라인 실행
GET  /api/v1/agents/status/{task_id}  # 비동기 작업 상태 확인
```

## 에이전트 간 데이터 흐름

```
┌─────────────────┐
│ 1. Structurer   │──→ Canonical 구조
└────────┬────────┘         │
         │                  ▼
         │    ┌─────────────────────────────────────┐
         │    │  2~6번 에이전트 공통 입력            │
         │    └─────────────────────────────────────┘
         │         │         │         │         │
         ▼         ▼         ▼         ▼         ▼
┌────────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│2.Eligibility│ │3.Track │ │4.Draft │ │5.Strategy│ │6.Risk  │
└────────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

## 환경 변수

```bash
# .env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
CORS_ORIGINS=http://localhost:3000

# Vector DB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# LLM 설정
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
```
