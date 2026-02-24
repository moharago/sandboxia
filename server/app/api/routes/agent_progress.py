"""에이전트 진행 상태 API

에이전트의 노드 목록 조회 및 진행 상태를 SSE로 구독하는 API입니다.
프론트엔드에서 로딩 화면에 단계별 진행 상태를 표시할 때 사용됩니다.
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import AuthUser, get_auth_user
from app.api.schemas.agent_progress import AGENT_NODES, NodeInfo, get_agent_nodes
from app.core.progress_store import progress_store
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
# 진행 상태 SSE 구독
# ===============================


@router.get(
    "/subscribe/{project_id}",
    summary="에이전트 진행 상태 구독 (SSE)",
    description="""
실행 중인 에이전트의 진행 상태를 SSE로 구독합니다.

## 사용 방법
1. mutation으로 에이전트 실행 시작
2. 이 엔드포인트로 SSE 연결하여 진행 상태 수신
3. agent_end 이벤트 수신 시 연결 종료

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
async def subscribe_progress(
    project_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
) -> StreamingResponse:
    """에이전트 진행 상태 SSE 구독"""
    # 프로젝트 권한 확인
    get_authorized_project(project_id, auth_user)

    return StreamingResponse(
        progress_store.subscribe(project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
