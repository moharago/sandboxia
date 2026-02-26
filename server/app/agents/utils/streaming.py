"""에이전트 스트리밍 유틸리티

LangGraph 에이전트 실행 시 progress_store와 연동하여 진행 상태를 추적합니다.
"""

import logging
from typing import Any

from app.core.progress_store import progress_store

logger = logging.getLogger(__name__)


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
        RuntimeError: 에이전트 실행 결과가 없습니다
    """
    if config is None:
        config = {"recursion_limit": 15}

    logger.info(f"[Streaming] 에이전트 실행 시작: {agent_type}, project={project_id}")

    # 진행 상태 추적 시작
    progress_store.start(project_id, agent_type)

    # 초기 상태를 복사하여 결과로 사용 (업데이트 병합용)
    result = dict(initial_state)

    try:
        # astream으로 실행하며 노드별 상태 업데이트 추적
        # stream_mode="updates"는 {node_name: state_update} 형태로 반환
        async for chunk in agent.astream(
            initial_state, config=config, stream_mode="updates"
        ):
            # chunk는 {node_name: state_update} 형태
            for node_name, state_update in chunk.items():
                # LangGraph 내부 노드 제외 (__start__, __end__ 등)
                if node_name and not node_name.startswith("__"):
                    logger.info(f"[Streaming] 노드 실행: {node_name}")

                    # 노드 시작 이벤트 (UI에서 spinner 표시용)
                    progress_store.update_node(project_id, node_name, "node_start")

                    # state_update를 result에 병합
                    if state_update and isinstance(state_update, dict):
                        result.update(state_update)

                    # 노드 완료 이벤트 (UI에서 체크 표시용)
                    progress_store.update_node(project_id, node_name, "node_end")

        logger.info(f"[Streaming] 에이전트 실행 완료: {agent_type}")

        # 진행 상태 완료
        progress_store.end(project_id)

    except Exception as e:
        progress_store.end(project_id, error=str(e))
        raise

    return result
