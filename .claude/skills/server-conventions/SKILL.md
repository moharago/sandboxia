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
