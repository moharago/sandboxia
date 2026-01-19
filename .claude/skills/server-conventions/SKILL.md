---
name: server-conventions
description: "Python/FastAPI/LangGraph 서버 코드 작성 컨벤션. 서버 코드 생성, API 엔드포인트 작성, AI 에이전트 구현, 비즈니스 로직 작업 시 사용. 트리거 - server 폴더 내 작업, FastAPI 라우터 생성, LangGraph 에이전트 구현, Pydantic 스키마 작성, 멀티 에이전트 시스템 설계"
---

# Server Conventions

Python, FastAPI, LangChain, LangGraph 기반 AI 에이전트 서버 코드 컨벤션.

## 기술 스택

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **AI**: LangChain, LangGraph
- **Vector DB**: Chroma (또는 추후 변경)
- **Package Manager**: uv
- **Validation**: Pydantic v2

## 프로젝트 구조

```
server/
├── app/
│   ├── agents/                 # LangGraph AI Agents
│   │   ├── __init__.py
│   │   ├── base.py            # 공통 에이전트 베이스
│   │   └── {agent_name}/
│   │       ├── __init__.py
│   │       ├── graph.py       # LangGraph 정의
│   │       ├── nodes.py       # 노드 함수들
│   │       ├── state.py       # 상태 정의
│   │       ├── tools.py       # 에이전트 도구
│   │       └── prompts.py     # 프롬프트 템플릿
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py            # 의존성 주입
│   │   ├── routes/            # API 엔드포인트
│   │   │   ├── __init__.py
│   │   │   └── {resource}.py
│   │   └── schemas/           # Pydantic 스키마
│   │       ├── __init__.py
│   │       └── {resource}.py
│   ├── services/              # 비즈니스 로직
│   │   ├── __init__.py
│   │   └── {service}.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # 설정 관리
│   │   └── exceptions.py      # 커스텀 예외
│   └── db/
│       ├── __init__.py
│       └── vector.py          # Vector DB 클라이언트
├── main.py
├── pyproject.toml
└── .env.example
```

## 네이밍 컨벤션

| 대상 | 컨벤션 | 예시 |
|------|--------|------|
| 파일/모듈 | snake_case | `user_service.py` |
| 클래스 | PascalCase | `UserService` |
| 함수/변수 | snake_case | `get_user_by_id` |
| 상수 | SCREAMING_SNAKE_CASE | `MAX_RETRIES` |
| Pydantic 모델 | PascalCase + 접미사 | `UserCreate`, `UserResponse` |
| 에이전트 폴더 | snake_case | `research_agent/` |
| 노드 함수 | snake_case + _node 접미사 | `retrieve_node`, `generate_node` |

## FastAPI 패턴

### 라우터 구조

```python
# api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user
from app.api.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(),
) -> UserResponse:
    """사용자 조회"""
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    user_service: UserService = Depends(),
) -> UserResponse:
    """사용자 생성"""
    return await user_service.create(data)
```

### 규칙

- 라우터별 prefix와 tags 설정
- response_model로 응답 타입 명시
- Depends()로 의존성 주입
- HTTPException으로 에러 처리
- async 함수 사용 권장

### 라우터 등록

```python
# main.py
from fastapi import FastAPI
from app.api.routes import users, agents, health

app = FastAPI(
    title="AI Agent API",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(users.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
```

## Pydantic 스키마 패턴

```python
# api/schemas/user.py
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """사용자 공통 필드"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """사용자 생성 요청"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """사용자 수정 요청"""
    email: EmailStr | None = None
    name: str | None = Field(None, min_length=1, max_length=100)


class UserResponse(UserBase):
    """사용자 응답"""
    id: str
    created_at: datetime
    
    model_config = {"from_attributes": True}
```

### 규칙

- Base → Create/Update → Response 계층 구조
- Field로 validation 규칙 명시
- Response 모델에 `from_attributes = True` 설정
- Optional 필드는 `| None` 사용

## LangGraph 에이전트 패턴

### 상태 정의

```python
# agents/research_agent/state.py
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ResearchState(TypedDict):
    """Research Agent 상태"""
    messages: Annotated[list, add_messages]
    query: str
    documents: list[str]
    answer: str | None
    iteration: int
```

### 노드 함수

```python
# agents/research_agent/nodes.py
from langchain_core.messages import AIMessage
from app.agents.research_agent.state import ResearchState


async def retrieve_node(state: ResearchState) -> dict:
    """문서 검색 노드"""
    query = state["query"]
    # 검색 로직
    documents = await vector_store.similarity_search(query, k=5)
    return {"documents": [doc.page_content for doc in documents]}


async def generate_node(state: ResearchState) -> dict:
    """답변 생성 노드"""
    documents = state["documents"]
    query = state["query"]
    
    response = await llm.ainvoke(
        GENERATE_PROMPT.format(context=documents, question=query)
    )
    
    return {
        "answer": response.content,
        "messages": [AIMessage(content=response.content)],
    }


async def grade_node(state: ResearchState) -> dict:
    """답변 품질 평가 노드"""
    # 평가 로직
    return {"iteration": state["iteration"] + 1}
```

### 그래프 정의

```python
# agents/research_agent/graph.py
from langgraph.graph import StateGraph, END
from app.agents.research_agent.state import ResearchState
from app.agents.research_agent.nodes import (
    retrieve_node,
    generate_node,
    grade_node,
)


def should_continue(state: ResearchState) -> str:
    """조건부 엣지: 계속 여부 결정"""
    if state["iteration"] >= 3:
        return "end"
    if state.get("answer"):
        return "end"
    return "retrieve"


def build_research_graph() -> StateGraph:
    """Research Agent 그래프 생성"""
    graph = StateGraph(ResearchState)
    
    # 노드 추가
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("grade", grade_node)
    
    # 엣지 정의
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "grade")
    graph.add_conditional_edges(
        "grade",
        should_continue,
        {
            "retrieve": "retrieve",
            "end": END,
        },
    )
    
    return graph.compile()


# 싱글톤 인스턴스
research_agent = build_research_graph()
```

### 도구 정의

```python
# agents/research_agent/tools.py
from langchain_core.tools import tool


@tool
def search_documents(query: str) -> list[str]:
    """벡터 DB에서 관련 문서 검색
    
    Args:
        query: 검색 쿼리
        
    Returns:
        관련 문서 리스트
    """
    # 검색 로직
    pass


@tool  
def calculate(expression: str) -> float:
    """수학 표현식 계산
    
    Args:
        expression: 계산할 수학 표현식
        
    Returns:
        계산 결과
    """
    return eval(expression)
```

### 프롬프트 관리

```python
# agents/research_agent/prompts.py
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You are a helpful research assistant.
Your goal is to provide accurate, well-researched answers."""

GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """Based on the following context, answer the question.

Context:
{context}

Question: {question}

Answer:"""),
])

GRADE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a grader assessing the quality of an answer."),
    ("human", """Question: {question}
Answer: {answer}

Is this answer accurate and complete? Respond with 'yes' or 'no'."""),
])
```

## 멀티 에이전트 패턴

### Supervisor 패턴

```python
# agents/supervisor/graph.py
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage


class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str | None


def supervisor_node(state: SupervisorState) -> dict:
    """다음 에이전트 결정"""
    # LLM으로 라우팅 결정
    response = llm.invoke(ROUTING_PROMPT.format(
        messages=state["messages"]
    ))
    return {"next_agent": response.content}


def route_to_agent(state: SupervisorState) -> str:
    """조건부 라우팅"""
    next_agent = state.get("next_agent", "end")
    if next_agent == "FINISH":
        return "end"
    return next_agent


def build_supervisor_graph():
    graph = StateGraph(SupervisorState)
    
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", research_agent)
    graph.add_node("writer", writer_agent)
    
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "researcher": "researcher",
            "writer": "writer",
            "end": END,
        },
    )
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("writer", "supervisor")
    
    return graph.compile()
```

## 서비스 레이어 패턴

```python
# services/user_service.py
from app.api.schemas.user import UserCreate, UserUpdate, UserResponse


class UserService:
    """사용자 관련 비즈니스 로직"""
    
    async def get_by_id(self, user_id: str) -> UserResponse | None:
        """ID로 사용자 조회"""
        pass
    
    async def create(self, data: UserCreate) -> UserResponse:
        """사용자 생성"""
        pass
    
    async def update(self, user_id: str, data: UserUpdate) -> UserResponse:
        """사용자 수정"""
        pass
```

## 설정 관리

```python
# core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str
    
    # Vector DB
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    
    # LLM
    openai_api_key: str
    model_name: str = "gpt-4o-mini"
    
    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

## 에러 처리

```python
# core/exceptions.py
from fastapi import HTTPException, status


class AppException(Exception):
    """애플리케이션 기본 예외"""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, id: str):
        super().__init__(
            message=f"{resource} with id '{id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class AgentExecutionError(AppException):
    def __init__(self, agent_name: str, detail: str):
        super().__init__(
            message=f"Agent '{agent_name}' execution failed: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
```

```python
# main.py - 예외 핸들러
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
```

## Import 순서

```python
# 1. 표준 라이브러리
from datetime import datetime
from typing import Annotated

# 2. 서드파티 라이브러리
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

# 3. 로컬 모듈
from app.core.config import settings
from app.api.schemas.user import UserCreate
from app.services.user_service import UserService
```

## 테스트 패턴

```python
# tests/test_agents/test_research_agent.py
import pytest
from app.agents.research_agent.graph import research_agent


@pytest.mark.asyncio
async def test_research_agent_basic_query():
    """기본 쿼리 테스트"""
    result = await research_agent.ainvoke({
        "messages": [],
        "query": "What is Python?",
        "documents": [],
        "answer": None,
        "iteration": 0,
    })

    assert result["answer"] is not None
    assert result["iteration"] <= 3
```

## 도메인 Tool 패턴 (SandboxIA)

이 프로젝트의 6개 에이전트에서 사용하는 Tool 패턴입니다.

### 1. 구조화 에이전트 Tools

```python
# agents/service_structurer/tools.py
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FormField(BaseModel):
    """폼 필드 스키마"""
    id: str
    label: str
    field_type: str  # text, table, checkbox, attachment
    required: bool
    section: str
    placeholder: str | None = None
    validation_rule: str | None = None


class ParsedTemplate(BaseModel):
    """파싱된 템플릿 구조"""
    sections: list[dict]
    fields: list[FormField]
    metadata: dict


@tool
def parse_application_template(file_path: str) -> ParsedTemplate:
    """신청서 템플릿을 파싱하여 섹션/필드 구조 추출

    Args:
        file_path: 신청서 파일 경로 (PDF/DOCX/HWP)

    Returns:
        섹션별 필드 구조, 필드 타입, 필수 여부
    """
    pass


@tool
def generate_form_schema(parsed_template: ParsedTemplate) -> dict:
    """파싱된 구조를 프론트엔드 Form JSON Schema로 변환

    Args:
        parsed_template: 파싱된 템플릿 구조

    Returns:
        필드 ID, 라벨, 도움말, validation rule 포함 스키마
    """
    pass


@tool
def auto_fill_fields(
    source_text: str,
    form_schema: dict,
) -> dict:
    """원문에서 필드별 초기값 자동 채움

    Args:
        source_text: 원문 텍스트
        form_schema: Form 스키마

    Returns:
        필드별 초깃값, 근거 위치, 신뢰도
    """
    pass


@tool
def convert_to_canonical(form_data: dict) -> dict:
    """확정된 Form 데이터를 내부 표준 구조로 변환

    Args:
        form_data: 사용자 확정 Form 데이터

    Returns:
        What/Who/How, 기능 분해, 데이터 흐름 등 표준 구조
    """
    pass
```

### 2. 대상성 판단 에이전트 Tools

```python
# agents/eligibility_evaluator/tools.py
from langchain_core.tools import tool
from pydantic import BaseModel


class EligibilitySignal(BaseModel):
    """대상성 시그널"""
    signal_type: str
    matched_keywords: list[str]
    confidence: float  # 0.0 ~ 1.0
    preliminary_label: str  # high, medium, low


class SimilarCase(BaseModel):
    """유사 승인 사례"""
    case_id: str
    summary: str
    similarity_score: float
    similarity_reason: str
    metadata: dict


@tool
def screen_eligibility_rules(canonical_structure: dict) -> EligibilitySignal:
    """규제/인허가/실증 필요 가능성 1차 스크리닝

    Args:
        canonical_structure: 표준화된 서비스 구조

    Returns:
        규제 시그널, 키워드 매칭 결과, 1차 라벨
    """
    pass


@tool
def search_similar_cases(
    canonical_structure: dict,
    signals: EligibilitySignal,
    top_k: int = 5,
) -> list[SimilarCase]:
    """유사 승인 사례 RAG 검색

    Args:
        canonical_structure: 표준화된 서비스 구조
        signals: 1차 스크리닝 시그널
        top_k: 반환할 사례 수

    Returns:
        유사 사례 목록 (요약, 유사 이유 포함)
    """
    pass


@tool
def compose_eligibility_decision(
    signals: EligibilitySignal,
    similar_cases: list[SimilarCase],
) -> dict:
    """최종 대상성 판정 및 근거 정리

    Args:
        signals: 1차 스크리닝 결과
        similar_cases: 유사 사례 검색 결과

    Returns:
        최종 라벨, 근거 bullet, 확신/리스크 표시
    """
    pass
```

### 3. 트랙 추천 에이전트 Tools

```python
# agents/track_recommender/tools.py
from langchain_core.tools import tool
from pydantic import BaseModel


class TrackScore(BaseModel):
    """트랙별 적합도 점수"""
    track_name: str  # 신속확인, 실증특례, 임시허가
    score: float
    matched_conditions: list[str]
    unmatched_conditions: list[str]


@tool
def score_track_eligibility(
    canonical_structure: dict,
    eligibility_summary: dict | None = None,
) -> list[TrackScore]:
    """트랙별 적합도 점수 산출

    Args:
        canonical_structure: 표준화된 서비스 구조
        eligibility_summary: 대상성 판단 요약 (있으면)

    Returns:
        신속확인/실증특례/임시허가 각 점수 및 조건 충족 여부
    """
    pass


@tool
def retrieve_track_definitions(
    candidate_tracks: list[str],
    key_points: list[str],
) -> list[dict]:
    """트랙 정의/요건 RAG 검색

    Args:
        candidate_tracks: 후보 트랙 목록
        key_points: 구조화 결과의 핵심 포인트

    Returns:
        트랙별 정의/요건 근거 스니펫 (출처 포함)
    """
    pass


@tool
def generate_track_recommendation(
    track_scores: list[TrackScore],
    track_definitions: list[dict],
) -> dict:
    """추천 트랙 및 사유 생성

    Args:
        track_scores: 트랙별 점수
        track_definitions: 트랙 정의 근거

    Returns:
        추천 트랙 1순위/차선, 추천 사유, 고객 설명용 문장
    """
    pass
```

### 4. 신청서 초안 에이전트 Tools

```python
# agents/application_drafter/tools.py
from langchain_core.tools import tool


@tool
def select_template(
    ministry: str,
    track: str,
    program: str,
) -> dict:
    """양식 선택 및 버전 매칭

    Args:
        ministry: 부처 (ICT융합, 스마트시티 등)
        track: 트랙 (신속확인/실증특례/임시허가)
        program: 프로그램 유형

    Returns:
        템플릿 ID, 섹션 목록, 필수 필드 스키마
    """
    pass


@tool
def map_section_content(
    canonical_structure: dict,
    eligibility_result: dict,
    recommendation_result: dict,
    template_schema: dict,
) -> dict:
    """섹션별 컨텐츠 매핑

    Args:
        canonical_structure: 표준화된 서비스 구조
        eligibility_result: 대상성 판단 결과
        recommendation_result: 트랙 추천 결과
        template_schema: 템플릿 스키마

    Returns:
        섹션별 채워넣을 데이터 JSON (출처 메타데이터 포함)
    """
    pass


@tool
def generate_section_text(section_data: dict) -> str:
    """섹션 문장 생성

    Args:
        section_data: 섹션별 매핑 데이터

    Returns:
        섹션별 초안 문단 (톤/형식 맞춤)
    """
    pass


@tool
def check_consistency(draft: str) -> dict:
    """일관성/중복/형식 검수

    Args:
        draft: 전체 초안

    Returns:
        용어 통일, 중복 제거, 누락 섹션 경고, 개선 포인트
    """
    pass


@tool
def render_document(
    final_draft: str,
    template_style: dict,
    output_format: str = "docx",
) -> str:
    """문서 렌더링 (DOCX/PDF)

    Args:
        final_draft: 최종 초안
        template_style: 회사 로고/서식 등
        output_format: docx 또는 pdf

    Returns:
        생성된 파일 경로
    """
    pass
```

### 5. 전략 추천 에이전트 Tools

```python
# agents/strategy_advisor/tools.py
from langchain_core.tools import tool


@tool
def cluster_similar_cases(
    canonical_structure: dict,
    track_candidates: list[str],
    top_k: int = 10,
) -> list[dict]:
    """유사 사례 군집 및 선정

    Args:
        canonical_structure: 표준화된 서비스 구조
        track_candidates: 트랙 후보
        top_k: 선정할 사례 수

    Returns:
        유사 사례 Top N + 비교 축 설명
    """
    pass


@tool
def extract_approval_patterns(cases: list[dict]) -> dict:
    """승인 포인트 패턴 추출

    Args:
        cases: 유사 사례 목록 (원문 요약/핵심 문장)

    Returns:
        반복되는 승인 포인트 (실증 범위, 안전/책임 등) + 빈도/중요도
    """
    pass


@tool
def generate_strategy(
    canonical_structure: dict,
    approval_patterns: dict,
) -> dict:
    """이번 건 적용 전략 생성

    Args:
        canonical_structure: 표준화된 서비스 구조
        approval_patterns: 추출된 승인 패턴

    Returns:
        강조 포인트, 피해야 할 서술, 구체 문장 가이드
    """
    pass


@tool
def provide_citation_snippets(
    strategy: dict,
    source_cases: list[dict],
) -> list[dict]:
    """근거 스니펫 및 인용 후보 제공

    Args:
        strategy: 생성된 전략
        source_cases: 사례 원문

    Returns:
        참고할 표현 (문장 단위), 출처/사례 ID, 적용 위치 추천
    """
    pass
```

### 6. 체크리스트/리스크 에이전트 Tools

```python
# agents/risk_checker/tools.py
from langchain_core.tools import tool
from pydantic import BaseModel


class ChecklistItem(BaseModel):
    """체크리스트 항목"""
    item_id: str
    criterion: str
    pass_condition: str
    evidence_example: str
    priority: str  # high, medium, low


class RiskItem(BaseModel):
    """리스크 항목"""
    location: str
    issue_type: str  # missing, weak, ambiguous, exaggerated
    severity: str  # high, medium, low
    description: str


@tool
def generate_checklist(
    track: str,
    ministry: str,
    canonical_structure: dict,
) -> list[ChecklistItem]:
    """기준 체크리스트 생성

    Args:
        track: 트랙
        ministry: 부처
        canonical_structure: 표준화된 서비스 구조

    Returns:
        필수 항목 체크리스트 (항목ID, 기준, 합격 조건, 증빙 예시)
    """
    pass


@tool
def detect_gaps(
    draft: str,
    checklist: list[ChecklistItem],
) -> list[RiskItem]:
    """초안 대비 누락/약점 탐지

    Args:
        draft: 신청서 초안
        checklist: 체크리스트

    Returns:
        누락 항목, 약한 항목 (근거 부족/모호/과장), 위험도
    """
    pass


@tool
def generate_risk_scenarios(risks: list[RiskItem]) -> list[dict]:
    """리스크 시나리오 생성

    Args:
        risks: 탐지된 리스크 항목

    Returns:
        예상 반려/보완 요청 포인트, 위험 이유 설명
    """
    pass


@tool
def suggest_improvements(
    problematic_text: str,
    risks: list[RiskItem],
    strategy: dict | None = None,
) -> list[dict]:
    """개선 문장/대체 표현 생성

    Args:
        problematic_text: 문제 문장
        risks: 리스크 분석 결과
        strategy: 전략 추천 결과 (있으면)

    Returns:
        수정 제안 문장 (전/후), 추가 근거 항목, 표현 톤 가이드
    """
    pass


@tool
def generate_final_report(
    checklist: list[ChecklistItem],
    risks: list[RiskItem],
    scenarios: list[dict],
    improvements: list[dict],
) -> dict:
    """최종 검수 리포트 생성

    Args:
        checklist: 체크리스트
        risks: 리스크 목록
        scenarios: 리스크 시나리오
        improvements: 개선 제안

    Returns:
        컨설턴트 제출용 리포트 (요약, 우선순위, TOP5 수정 항목)
    """
    pass
```

### Tool 작성 규칙

1. **Pydantic 모델 사용**: 복잡한 입출력은 Pydantic 모델로 정의
2. **docstring 필수**: Args, Returns 명시 (LLM이 Tool 선택 시 참조)
3. **단일 책임**: 하나의 Tool은 하나의 명확한 역할만 수행
4. **출처 메타데이터**: RAG 결과는 항상 출처 정보 포함
5. **신뢰도/점수**: 판단 결과에는 신뢰도나 점수 포함

## 공용 Tool 패턴 (Shared Tools)

### RAG Tools (R1, R2, R3)

모든 에이전트가 공용으로 사용하는 RAG Tool 패턴입니다.

```python
# tools/shared/rag/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from langchain_core.tools import tool


class RAGResult(BaseModel):
    """RAG 검색 결과 표준 포맷"""
    content: str
    source_id: str
    source_type: str  # regulation, case, law
    page: int | None = None
    paragraph: int | None = None
    relevance_score: float
    snippet: str


class BaseRAGTool(ABC):
    """RAG Tool 기본 클래스"""

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[RAGResult]:
        pass

    @abstractmethod
    def get_corpus_type(self) -> str:
        pass
```

```python
# tools/shared/rag/regulation_rag.py
from langchain_core.tools import tool
from app.tools.shared.rag.base import RAGResult


@tool
def search_regulation(
    query: str,
    track: str | None = None,
    top_k: int = 5,
) -> list[RAGResult]:
    """R1. 규제제도 & 절차 RAG 검색

    제도 정의(신속확인/실증특례/임시허가), 절차, 제출 요건, 심사 포인트 검색.

    Args:
        query: 검색 쿼리
        track: 특정 트랙 필터 (optional)
        top_k: 반환할 결과 수

    Returns:
        관련 규제 제도 정보 리스트
    """
    pass


@tool
def search_cases(
    query: str,
    status: str | None = None,  # approved, rejected
    domain: str | None = None,
    top_k: int = 5,
) -> list[RAGResult]:
    """R2. 승인 사례 RAG 검색

    승인/반려 사례, 조건, 실증 범위, 안전·책임, 소비자 고지 검색.

    Args:
        query: 검색 쿼리
        status: 승인 상태 필터 (optional)
        domain: 도메인 필터 (optional)
        top_k: 반환할 결과 수

    Returns:
        관련 승인 사례 리스트
    """
    pass


@tool
def search_domain_law(
    query: str,
    domain: str,
    law_type: str | None = None,  # law, permit, regulation
    top_k: int = 5,
) -> list[RAGResult]:
    """R3. 도메인별 규제·법령 RAG 검색

    분야별 주요 법령/인허가 체계, 규제 쟁점 검색.

    Args:
        query: 검색 쿼리
        domain: 도메인 (의료, 금융, 모빌리티 등)
        law_type: 법령 유형 필터 (optional)
        top_k: 반환할 결과 수

    Returns:
        관련 법령/인허가 정보 리스트
    """
    pass
```

### Utility Tools (C0, C1, C2)

```python
# tools/shared/utils/evidence.py
from langchain_core.tools import tool
from pydantic import BaseModel


class Evidence(BaseModel):
    """인용/출처 표준 포맷"""
    evidence_id: str
    source_id: str
    source_type: str
    page: int | None
    paragraph: int | None
    snippet: str
    context: str | None = None


class EvidenceStore:
    """C0. Evidence/인용 관리"""

    def __init__(self):
        self._store: dict[str, Evidence] = {}

    def add(self, evidence: Evidence) -> str:
        """인용 추가"""
        self._store[evidence.evidence_id] = evidence
        return evidence.evidence_id

    def get(self, evidence_id: str) -> Evidence | None:
        """인용 조회"""
        return self._store.get(evidence_id)

    def get_by_source(self, source_id: str) -> list[Evidence]:
        """소스별 인용 조회"""
        return [e for e in self._store.values() if e.source_id == source_id]

    def to_citation_format(self, evidence_id: str) -> str:
        """인용 포맷으로 변환"""
        evidence = self.get(evidence_id)
        if not evidence:
            return ""
        return f"[{evidence.source_type}:{evidence.source_id}, p.{evidence.page}]"
```

```python
# tools/shared/utils/canonical.py
from langchain_core.tools import tool
from pydantic import BaseModel


class CanonicalStructure(BaseModel):
    """C1. 서비스 표준 구조"""
    service_id: str

    # What - 서비스 정의
    what: dict  # name, description, core_features

    # Who - 이해관계자
    who: dict  # provider, users, regulators

    # How - 운영 방식
    how: dict  # technology, data_flow, process

    # 기능 분해
    functions: list[dict]

    # 규제 쟁점
    regulatory_issues: list[dict]

    # 메타데이터
    metadata: dict


@tool
def convert_to_canonical(form_data: dict) -> CanonicalStructure:
    """C1. Form 데이터를 Canonical 구조로 변환

    확정된 Form 데이터를 내부 표준 구조(What/Who/How)로 변환.
    이 구조는 2~6번 에이전트의 공통 입력으로 사용됨.

    Args:
        form_data: 사용자 확정 Form 데이터

    Returns:
        Canonical 표준 구조
    """
    pass


@tool
def extract_canonical_summary(canonical: CanonicalStructure) -> str:
    """Canonical 구조에서 요약 추출

    Args:
        canonical: Canonical 구조

    Returns:
        서비스 요약 텍스트
    """
    pass
```

```python
# tools/shared/utils/patch.py
from langchain_core.tools import tool
from pydantic import BaseModel
from datetime import datetime


class PatchRecord(BaseModel):
    """변경 이력 레코드"""
    patch_id: str
    timestamp: datetime
    field_path: str
    old_value: str | None
    new_value: str
    changed_by: str
    reason: str | None = None


class PatchResult(BaseModel):
    """패치 적용 결과"""
    success: bool
    updated_data: dict
    patch_records: list[PatchRecord]
    conflicts: list[dict] | None = None


@tool
def apply_patch(
    original_data: dict,
    diff: dict,
    changed_by: str,
    reason: str | None = None,
) -> PatchResult:
    """C2. 증분 수정 적용

    사용자 수정 diff를 반영하고 변경 이력 기록.

    Args:
        original_data: 원본 데이터
        diff: 변경 사항 (필드 경로: 새 값)
        changed_by: 수정자
        reason: 수정 사유 (optional)

    Returns:
        업데이트된 데이터 + 변경 이력
    """
    pass


@tool
def merge_patches(
    base_data: dict,
    patches: list[dict],
) -> PatchResult:
    """C2. 여러 패치 병합

    여러 버전의 수정 사항을 병합.

    Args:
        base_data: 기준 데이터
        patches: 패치 리스트

    Returns:
        병합된 데이터 + 충돌 정보
    """
    pass


@tool
def get_patch_history(
    data_id: str,
    field_path: str | None = None,
) -> list[PatchRecord]:
    """C2. 변경 이력 조회

    Args:
        data_id: 데이터 ID
        field_path: 특정 필드 경로 (optional)

    Returns:
        변경 이력 리스트
    """
    pass
```

### 공용 Tool 사용 예시

```python
# agents/eligibility_evaluator/nodes.py
from app.tools.shared.rag.regulation_rag import search_regulation, search_cases
from app.tools.shared.utils.evidence import EvidenceStore


async def evaluate_node(state: EligibilityState) -> dict:
    """대상성 판단 노드"""
    canonical = state["canonical"]
    evidence_store = EvidenceStore()

    # 공용 RAG Tool 사용
    regulation_results = await search_regulation(
        query=canonical.what["description"],
        top_k=5,
    )

    case_results = await search_cases(
        query=canonical.what["description"],
        domain=canonical.metadata.get("domain"),
        top_k=5,
    )

    # 인용 관리
    for result in regulation_results + case_results:
        evidence_store.add(Evidence(
            evidence_id=f"ev_{result.source_id}",
            source_id=result.source_id,
            source_type=result.source_type,
            page=result.page,
            paragraph=result.paragraph,
            snippet=result.snippet,
        ))

    return {
        "regulation_results": regulation_results,
        "case_results": case_results,
        "evidence_store": evidence_store,
    }
```
