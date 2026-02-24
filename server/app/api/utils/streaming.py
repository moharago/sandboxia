"""SSE 스트리밍 유틸리티

LangGraph 에이전트의 진행 상태를 Server-Sent Events로 스트리밍합니다.
"""

import json
import logging
import shutil
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.api.schemas.agent_progress import (
    AgentProgressEvent,
    calculate_progress,
    get_node_label,
)
from app.services.parsers import DocumentSubtype

logger = logging.getLogger(__name__)


def format_sse_event(event: AgentProgressEvent) -> str:
    """SSE 형식으로 이벤트 포맷팅"""
    data = event.model_dump_json()
    return f"data: {data}\n\n"


async def stream_agent_progress(
    agent: Any,
    initial_state: dict,
    agent_type: str,
    config: dict | None = None,
) -> AsyncGenerator[str, None]:
    """에이전트 실행하며 진행 상태를 SSE로 스트리밍

    Args:
        agent: 컴파일된 LangGraph 에이전트
        initial_state: 에이전트 초기 상태
        agent_type: 에이전트 타입 (eligibility_evaluator, track_recommender 등)
        config: LangGraph 설정 (recursion_limit 등)

    Yields:
        SSE 형식의 진행 이벤트 문자열
    """
    if config is None:
        config = {"recursion_limit": 15}

    completed_nodes: list[str] = []

    # 에이전트 시작 이벤트
    start_event = AgentProgressEvent(
        event_type="agent_start",
        agent_type=agent_type,
        progress=0,
        message="분석을 시작합니다...",
        completed_nodes=[],
    )
    yield format_sse_event(start_event)

    try:
        # LangGraph의 astream_events 사용
        async for event in agent.astream_events(initial_state, config=config, version="v2"):
            event_kind = event.get("event")

            # 노드 시작 이벤트
            if event_kind == "on_chain_start":
                node_name = event.get("name", "")
                # LangGraph 내부 노드 제외 (LangGraph, RunnableSequence 등)
                if node_name and not node_name.startswith(("Lang", "Runnable", "__")):
                    node_label = get_node_label(agent_type, node_name)
                    progress = calculate_progress(agent_type, completed_nodes)

                    progress_event = AgentProgressEvent(
                        event_type="node_start",
                        agent_type=agent_type,
                        node_id=node_name,
                        node_label=node_label,
                        progress=progress,
                        message=f"{node_label} 진행 중...",
                        completed_nodes=completed_nodes.copy(),
                    )
                    yield format_sse_event(progress_event)

            # 노드 종료 이벤트
            elif event_kind == "on_chain_end":
                node_name = event.get("name", "")
                if node_name and not node_name.startswith(("Lang", "Runnable", "__")):
                    if node_name not in completed_nodes:
                        completed_nodes.append(node_name)

                    node_label = get_node_label(agent_type, node_name)
                    progress = calculate_progress(agent_type, completed_nodes)

                    progress_event = AgentProgressEvent(
                        event_type="node_end",
                        agent_type=agent_type,
                        node_id=node_name,
                        node_label=node_label,
                        progress=progress,
                        message=f"{node_label} 완료",
                        completed_nodes=completed_nodes.copy(),
                    )
                    yield format_sse_event(progress_event)

        # 에이전트 완료 이벤트
        end_event = AgentProgressEvent(
            event_type="agent_end",
            agent_type=agent_type,
            progress=100,
            message="분석이 완료되었습니다.",
            completed_nodes=completed_nodes.copy(),
        )
        yield format_sse_event(end_event)

    except Exception as e:
        logger.error(f"에이전트 스트리밍 중 오류: {e}", exc_info=True)
        error_event = AgentProgressEvent(
            event_type="error",
            agent_type=agent_type,
            progress=calculate_progress(agent_type, completed_nodes),
            message=f"오류가 발생했습니다: {str(e)}",
            completed_nodes=completed_nodes.copy(),
        )
        yield format_sse_event(error_event)
        raise


# 트랙별 서브타입 매핑
TRACK_SUBTYPE_MAP: dict[str, list[DocumentSubtype]] = {
    "counseling": [DocumentSubtype.COUNSELING_APPLICATION],
    "quick_check": [
        DocumentSubtype.FASTCHECK_APPLICATION,
        DocumentSubtype.FASTCHECK_DESCRIPTION,
    ],
    "temp_permit": [
        DocumentSubtype.TEMPORARY_APPLICATION,
        DocumentSubtype.TEMPORARY_BUSINESS_PLAN,
        DocumentSubtype.TEMPORARY_JUSTIFICATION,
        DocumentSubtype.TEMPORARY_SAFETY,
    ],
    "demo": [
        DocumentSubtype.DEMONSTRATION_APPLICATION,
        DocumentSubtype.DEMONSTRATION_PLAN,
        DocumentSubtype.DEMONSTRATION_JUSTIFICATION,
        DocumentSubtype.DEMONSTRATION_PROTECTION,
    ],
}


async def stream_service_structurer_progress(
    agent: Any,
    session_id: str,
    requested_track: str,
    consultant_input: dict,
    files: list[UploadFile],
    config: dict | None = None,
) -> AsyncGenerator[str, None]:
    """Service Structurer 에이전트를 실행하며 진행 상태를 SSE로 스트리밍

    Args:
        agent: 컴파일된 LangGraph 에이전트
        session_id: 세션 ID (= project_id)
        requested_track: 트랙 (counseling/quick_check/temp_permit/demo)
        consultant_input: 컨설턴트 입력 데이터 (dict)
        files: 업로드 파일 목록
        config: LangGraph 설정

    Yields:
        SSE 형식의 진행 이벤트 문자열
    """
    if config is None:
        config = {"recursion_limit": 15}

    agent_type = "service_structurer"
    completed_nodes: list[str] = []

    # 에이전트 시작 이벤트
    start_event = AgentProgressEvent(
        event_type="agent_start",
        agent_type=agent_type,
        progress=0,
        message="서비스 분석을 시작합니다...",
        completed_nodes=[],
    )
    yield format_sse_event(start_event)

    temp_dir = tempfile.mkdtemp()

    try:
        # 파일 처리
        expected_subtypes = TRACK_SUBTYPE_MAP.get(requested_track, [])
        file_paths: list[str] = []
        file_subtypes: list[str] = []

        for idx, upload_file in enumerate(files):
            if not upload_file.filename:
                continue

            filename = upload_file.filename
            temp_path = Path(temp_dir) / f"{idx}_{filename}"

            content = await upload_file.read()
            with open(temp_path, "wb") as f:
                f.write(content)

            subtype = expected_subtypes[idx] if idx < len(expected_subtypes) else None
            subtype_str = subtype.value if subtype else "unknown"

            file_paths.append(str(temp_path))
            file_subtypes.append(subtype_str)

        # 초기 상태 구성
        initial_state = {
            "messages": [],
            "session_id": session_id,
            "requested_track": requested_track,
            "consultant_input": consultant_input,
            "file_paths": file_paths,
            "file_subtypes": file_subtypes,
            "hwp_parse_results": [],
            "canonical_structure": None,
            "error": None,
        }

        # LangGraph의 astream_events 사용
        async for event in agent.astream_events(initial_state, config=config, version="v2"):
            event_kind = event.get("event")

            # 노드 시작 이벤트
            if event_kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name and not node_name.startswith(("Lang", "Runnable", "__")):
                    node_label = get_node_label(agent_type, node_name)
                    progress = calculate_progress(agent_type, completed_nodes)

                    progress_event = AgentProgressEvent(
                        event_type="node_start",
                        agent_type=agent_type,
                        node_id=node_name,
                        node_label=node_label,
                        progress=progress,
                        message=f"{node_label} 진행 중...",
                        completed_nodes=completed_nodes.copy(),
                    )
                    yield format_sse_event(progress_event)

            # 노드 종료 이벤트
            elif event_kind == "on_chain_end":
                node_name = event.get("name", "")
                if node_name and not node_name.startswith(("Lang", "Runnable", "__")):
                    if node_name not in completed_nodes:
                        completed_nodes.append(node_name)

                    node_label = get_node_label(agent_type, node_name)
                    progress = calculate_progress(agent_type, completed_nodes)

                    progress_event = AgentProgressEvent(
                        event_type="node_end",
                        agent_type=agent_type,
                        node_id=node_name,
                        node_label=node_label,
                        progress=progress,
                        message=f"{node_label} 완료",
                        completed_nodes=completed_nodes.copy(),
                    )
                    yield format_sse_event(progress_event)

        # 에이전트 완료 이벤트
        end_event = AgentProgressEvent(
            event_type="agent_end",
            agent_type=agent_type,
            progress=100,
            message="서비스 분석이 완료되었습니다.",
            completed_nodes=completed_nodes.copy(),
        )
        yield format_sse_event(end_event)

    except Exception as e:
        logger.error(f"Service Structurer 스트리밍 중 오류: {e}", exc_info=True)
        error_event = AgentProgressEvent(
            event_type="error",
            agent_type=agent_type,
            progress=calculate_progress(agent_type, completed_nodes),
            message=f"오류가 발생했습니다: {str(e)}",
            completed_nodes=completed_nodes.copy(),
        )
        yield format_sse_event(error_event)
        raise

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
