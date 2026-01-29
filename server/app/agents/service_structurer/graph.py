"""Service Structurer Agent 그래프 정의

LangGraph StateGraph를 사용하여 에이전트 워크플로우를 정의합니다.

플로우:
    START → parse_hwp → build_structure → END
"""

from langgraph.graph import END, StateGraph

from app.agents.service_structurer.nodes import (
    build_structure_node,
    parse_hwp_node,
)
from app.agents.service_structurer.state import ServiceStructurerState


def should_continue_after_parse(state: ServiceStructurerState) -> str:
    """파싱 후 계속 진행할지 결정

    에러가 있어도 build_structure로 진행합니다.
    (컨설턴트 입력만으로도 구조 생성 가능)
    """
    # 에러가 있고 파싱 결과도 없으며 컨설턴트 입력도 없으면 종료
    if state.get("error"):
        if not state.get("hwp_parse_results") and not state.get("consultant_input"):
            return "end"
    return "build_structure"


def build_service_structurer_graph() -> StateGraph:
    """Service Structurer Agent 그래프 생성

    Returns:
        컴파일된 StateGraph
    """
    # 그래프 생성
    graph = StateGraph(ServiceStructurerState)

    # 노드 추가
    graph.add_node("parse_hwp", parse_hwp_node)
    graph.add_node("build_structure", build_structure_node)

    # 엣지 정의
    graph.set_entry_point("parse_hwp")

    # 조건부 엣지: 파싱 후 구조 생성 또는 종료
    graph.add_conditional_edges(
        "parse_hwp",
        should_continue_after_parse,
        {
            "build_structure": "build_structure",
            "end": END,
        },
    )

    # 구조 생성 후 종료
    graph.add_edge("build_structure", END)

    return graph.compile()


# 싱글톤 에이전트 인스턴스
service_structurer_agent = build_service_structurer_graph()


async def run_service_structurer(
    session_id: str,
    requested_track: str,
    consultant_input: dict,
    file_paths: list[str] | None = None,
    file_subtypes: list[str] | None = None,
) -> dict:
    """Service Structurer Agent 실행 헬퍼 함수

    Args:
        session_id: 세션 ID
        requested_track: 요청된 트랙 (counseling/fastcheck/temporary/demonstration)
        consultant_input: 컨설턴트 입력 데이터
        file_paths: HWP 파일 경로 리스트 (optional)
        file_subtypes: 각 파일의 서브타입 리스트 (optional)

    Returns:
        실행 결과 (canonical_structure 포함)
    """
    initial_state: ServiceStructurerState = {
        "messages": [],
        "session_id": session_id,
        "requested_track": requested_track,
        "consultant_input": consultant_input,
        "file_paths": file_paths or [],
        "file_subtypes": file_subtypes or [],
        "hwp_parse_results": [],
        "canonical_structure": None,
        "error": None,
    }

    result = await service_structurer_agent.ainvoke(initial_state)

    return {
        "session_id": session_id,
        "canonical_structure": result.get("canonical_structure"),
        "hwp_parse_results": result.get("hwp_parse_results", []),
        "error": result.get("error"),
        "messages": [
            {"role": "assistant", "content": m.content}
            for m in result.get("messages", [])
            if hasattr(m, "content")
        ],
    }
