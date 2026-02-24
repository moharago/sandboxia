"""에이전트 진행 상태 스트리밍 API

각 에이전트의 실행 진행 상태를 SSE(Server-Sent Events)로 스트리밍합니다.
프론트엔드에서 로딩 화면에 단계별 진행 상태를 표시할 때 사용됩니다.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.application_drafter.graph import build_application_drafter_graph
from app.agents.eligibility_evaluator.graph import compile_eligibility_graph
from app.agents.service_structurer.graph import build_service_structurer_graph
from app.agents.track_recommender.graph import build_track_recommender_graph
from app.api.deps import AuthUser, get_auth_user
from app.api.schemas.agent_progress import AGENT_NODES, NodeInfo, get_agent_nodes
from app.api.utils.streaming import stream_agent_progress, stream_service_structurer_progress
from app.services.project_service import get_authorized_project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/progress", tags=["agent-progress"])


# ===============================
# 에이전트 노드 정보 조회
# ===============================


class AgentNodesResponse(BaseModel):
    """에이전트 노드 목록 응답"""
    agent_type: str
    nodes: list[NodeInfo]
    total_steps: int


@router.get(
    "/nodes/{agent_type}",
    response_model=AgentNodesResponse,
    summary="에이전트 노드 목록 조회",
    description="에이전트의 실행 단계(노드) 목록을 반환합니다. 로딩 화면 UI 구성에 사용합니다.",
)
async def get_agent_nodes_info(
    agent_type: Literal["service_structurer", "eligibility_evaluator", "track_recommender", "application_drafter"],
) -> AgentNodesResponse:
    """에이전트의 노드 목록 반환"""
    nodes = get_agent_nodes(agent_type)
    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"알 수 없는 에이전트 타입: {agent_type}",
        )

    return AgentNodesResponse(
        agent_type=agent_type,
        nodes=nodes,
        total_steps=len(nodes),
    )


@router.get(
    "/nodes",
    response_model=dict[str, AgentNodesResponse],
    summary="전체 에이전트 노드 목록 조회",
    description="모든 에이전트의 실행 단계(노드) 목록을 반환합니다.",
)
async def get_all_agent_nodes() -> dict[str, AgentNodesResponse]:
    """모든 에이전트의 노드 목록 반환"""
    result = {}
    for agent_type, nodes in AGENT_NODES.items():
        result[agent_type] = AgentNodesResponse(
            agent_type=agent_type,
            nodes=nodes,
            total_steps=len(nodes),
        )
    return result


# ===============================
# 스트리밍 엔드포인트
# ===============================


class StreamRequest(BaseModel):
    """스트리밍 요청"""
    project_id: str


@router.post(
    "/stream/service",
    summary="서비스 구조화 진행 상태 스트리밍",
    description="서비스 구조화 에이전트를 실행하면서 진행 상태를 SSE로 스트리밍합니다.",
)
async def stream_service_progress(
    session_id: str = Form(..., description="프로젝트 ID"),
    requested_track: str = Form(..., description="트랙 (counseling/quick_check/temp_permit/demo)"),
    consultant_input: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    auth_user: AuthUser = Depends(get_auth_user),
) -> StreamingResponse:
    """서비스 구조화 진행 상태 스트리밍"""
    import json

    # 프로젝트 조회 + 권한 확인
    get_authorized_project(session_id, auth_user)

    # consultant_input JSON 파싱
    try:
        consultant_data = json.loads(consultant_input)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"consultant_input JSON 파싱 오류: {str(e)}",
        )

    # 에이전트 빌드
    agent = build_service_structurer_graph()

    return StreamingResponse(
        stream_service_structurer_progress(
            agent=agent,
            session_id=session_id,
            requested_track=requested_track,
            consultant_input=consultant_data,
            files=files,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/stream/eligibility",
    summary="대상성 판단 진행 상태 스트리밍",
    description="""
대상성 판단 에이전트를 실행하면서 진행 상태를 SSE로 스트리밍합니다.

## SSE 이벤트 형식
```json
{
    "event_type": "node_start" | "node_end" | "agent_start" | "agent_end" | "error",
    "agent_type": "eligibility_evaluator",
    "node_id": "screen",
    "node_label": "규제 탐지",
    "progress": 25,
    "message": "규제 탐지 진행 중...",
    "completed_nodes": ["screen"]
}
```
    """,
)
async def stream_eligibility_progress(
    request: StreamRequest,
    auth_user: AuthUser = Depends(get_auth_user),
) -> StreamingResponse:
    """대상성 판단 진행 상태 스트리밍"""
    project_id = request.project_id

    # 프로젝트 조회 + 권한 확인
    project = get_authorized_project(project_id, auth_user)

    canonical = project.get("canonical")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트에 서비스 정보(canonical)가 없습니다. Step 1을 먼저 완료하세요.",
        )

    # 에이전트 빌드
    agent = compile_eligibility_graph()

    # 초기 상태
    initial_state = {
        "project_id": project_id,
        "canonical": canonical,
    }

    return StreamingResponse(
        stream_agent_progress(agent, initial_state, "eligibility_evaluator"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/stream/track",
    summary="트랙 추천 진행 상태 스트리밍",
    description="트랙 추천 에이전트를 실행하면서 진행 상태를 SSE로 스트리밍합니다.",
)
async def stream_track_progress(
    request: StreamRequest,
    auth_user: AuthUser = Depends(get_auth_user),
) -> StreamingResponse:
    """트랙 추천 진행 상태 스트리밍"""
    project_id = request.project_id

    # 프로젝트 조회 + 권한 확인
    project = get_authorized_project(project_id, auth_user)

    canonical = project.get("canonical")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트에 서비스 정보(canonical)가 없습니다. Step 1을 먼저 완료하세요.",
        )

    # 에이전트 빌드
    agent = build_track_recommender_graph()

    # 초기 상태
    initial_state = {
        "project_id": project_id,
        "canonical": canonical,
    }

    return StreamingResponse(
        stream_agent_progress(agent, initial_state, "track_recommender"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/stream/draft",
    summary="신청서 초안 생성 진행 상태 스트리밍",
    description="신청서 초안 생성 에이전트를 실행하면서 진행 상태를 SSE로 스트리밍합니다.",
)
async def stream_draft_progress(
    request: StreamRequest,
    auth_user: AuthUser = Depends(get_auth_user),
) -> StreamingResponse:
    """신청서 초안 생성 진행 상태 스트리밍"""
    project_id = request.project_id

    # 프로젝트 조회 + 권한 확인
    project = get_authorized_project(project_id, auth_user)

    canonical = project.get("canonical")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트에 서비스 정보(canonical)가 없습니다. Step 1을 먼저 완료하세요.",
        )

    track = project.get("track")
    if not track:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="트랙이 선택되지 않았습니다. Step 3을 먼저 완료하세요.",
        )

    # 에이전트 빌드
    agent = build_application_drafter_graph()

    # 초기 상태
    initial_state = {
        "project_id": project_id,
        "canonical": canonical,
        "track": track,
    }

    return StreamingResponse(
        stream_agent_progress(agent, initial_state, "application_drafter"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
