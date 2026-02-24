"""에이전트 스트리밍 유틸리티

LangGraph 에이전트 실행 시 progress_store와 연동하여 진행 상태를 추적합니다.
"""

from typing import Any

from app.core.progress_store import progress_store


async def run_agent_with_progress(
    agent: Any,
    initial_state: dict,
    project_id: str,
    agent_type: str,
    config: dict | None = None,
) -> dict:
    """에이전트를 실행하며 진행 상태를 추적

    Args:
        agent: 컴파일된 LangGraph 에이전트
        initial_state: 초기 상태
        project_id: 프로젝트 ID
        agent_type: 에이전트 타입 (eligibility_evaluator, track_recommender 등)
        config: LangGraph 설정

    Returns:
        에이전트 실행 결과 (마지막 상태)

    Raises:
        RuntimeError: 에이전트 실행 결과가 없을 때
    """
    if config is None:
        config = {"recursion_limit": 15}

    # 진행 상태 추적 시작
    progress_store.start(project_id, agent_type)

    result = None
    try:
        # astream_events로 실행하며 진행 상태 추적
        async for event in agent.astream_events(
            initial_state, config=config, version="v2"
        ):
            event_kind = event.get("event")
            node_name = event.get("name", "")

            # LangGraph 내부 노드 제외
            if node_name and not node_name.startswith(("Lang", "Runnable", "__")):
                if event_kind == "on_chain_start":
                    progress_store.update_node(project_id, node_name, "node_start")
                elif event_kind == "on_chain_end":
                    progress_store.update_node(project_id, node_name, "node_end")
                    # 마지막 이벤트의 output에서 결과 추출
                    output = event.get("data", {}).get("output")
                    if output and isinstance(output, dict):
                        result = output

        # 진행 상태 완료
        progress_store.end(project_id)

    except Exception as e:
        progress_store.end(project_id, error=str(e))
        raise

    if not result:
        raise RuntimeError("에이전트 실행 결과가 없습니다")

    return result
