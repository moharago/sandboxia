from functools import lru_cache
import operator
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agents.sample_calculator.graph import calculator_node
from app.agents.sample_researcher.graph import researcher_node
from app.core.config import settings


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str
    iteration_count: int


llm = ChatOpenAI(
    model="gpt-4.1-nano",
    temperature=0,
    api_key=settings.OPENAI_API_KEY,
)

SUPERVISOR_PROMPT = """
당신은 팀 관리자입니다. 작업을 적절한 팀원에게 할당하세요.

팀원:
- researcher: 웹 검색, 최신 정보 조사
- calculator: 수학 계산, 날짜/시간 계산

지시사항:
1. 사용자 요청을 분석하세요.
2. 아직 작업이 안 된 부분이 있으면 적절한 팀원을 다시 선택하세요.
3. 이미 충분히 답변했다면, FINISH를 선택하세요.
4. 한번에 한명만 선택하세요.

다음 중 하나만 응답:
researcher, calculator, FINISH
""".strip()


def supervisor_node(state: AgentState):
    iteration = state.get("iteration_count", 0) + 1
    if iteration > 5:
        return {"messages": [], "next": "FINISH", "iteration_count": iteration}

    messages = [
        SystemMessage(content=SUPERVISOR_PROMPT),
        *state["messages"],
    ]
    response = llm.invoke(messages)
    content = (response.content or "").lower()

    if "researcher" in content and iteration <= 5:
        next_agent = "researcher"
    elif "calculator" in content and iteration <= 5:
        next_agent = "calculator"
    else:
        next_agent = "FINISH"

    if next_agent == "FINISH":
        final_response = llm.invoke(
            [
                SystemMessage(content="팀원들의 정보를 종합해서 답변을 작성하세요."),
                *state["messages"],
            ]
        )
        return {
            "messages": [final_response],
            "next": "FINISH",
            "iteration_count": iteration,
        }

    return {
        "messages": [response],
        "next": next_agent,
        "iteration_count": iteration,
    }


def router(state: AgentState) -> Literal["researcher", "calculator", "FINISH"]:
    return state["next"]


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("calculator", calculator_node)
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "researcher": "researcher",
            "calculator": "calculator",
            "FINISH": END,
        },
    )
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("calculator", "supervisor")
    return workflow.compile()


@lru_cache(maxsize=1)
def get_graph():
    return build_graph()
