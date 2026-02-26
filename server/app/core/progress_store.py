"""에이전트 진행 상태 저장소

실행 중인 에이전트의 진행 상태를 저장하고 SSE로 구독할 수 있게 합니다.

사용 방법:
1. 에이전트 실행 시 progress_store.start(project_id, agent_type) 호출
2. 노드 시작/종료 시 progress_store.update_node(...) 호출
3. 에이전트 종료 시 progress_store.end(project_id) 호출
4. 클라이언트는 progress_store.subscribe(project_id)로 SSE 구독
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Literal

from app.api.schemas.agent_progress import (
    AgentProgressEvent,
    calculate_progress,
    get_node_label,
)

logger = logging.getLogger(__name__)

EventType = Literal["agent_start", "node_start", "node_end", "agent_end", "error"]


@dataclass
class ProgressState:
    """프로젝트별 진행 상태"""
    project_id: str
    agent_type: str
    completed_nodes: list[str] = field(default_factory=list)
    current_node: str | None = None
    progress: int = 0
    message: str | None = None
    is_complete: bool = False
    error: str | None = None
    # SSE 구독자들에게 이벤트 전달을 위한 Queue
    subscribers: list[asyncio.Queue] = field(default_factory=list)


class ProgressStore:
    """에이전트 진행 상태 저장소 (싱글톤)"""

    def __init__(self):
        self._states: dict[str, ProgressState] = {}

    def _format_sse(self, event: AgentProgressEvent) -> str:
        """SSE 형식으로 이벤트 포맷팅"""
        data = event.model_dump_json()
        return f"data: {data}\n\n"

    async def _broadcast(self, project_id: str, event: AgentProgressEvent) -> None:
        """모든 구독자에게 이벤트 전송"""
        state = self._states.get(project_id)
        if not state:
            logger.warning(f"[ProgressStore] 브로드캐스트 실패 - 상태 없음: {project_id}")
            return

        subscriber_count = len(state.subscribers)
        if subscriber_count == 0:
            logger.warning(f"[ProgressStore] 브로드캐스트 실패 - 구독자 없음: {project_id}, 이벤트: {event.event_type}")
            return

        sse_data = self._format_sse(event)
        logger.info(f"[ProgressStore] 브로드캐스트: {event.event_type} -> {subscriber_count}명")
        for queue in state.subscribers:
            try:
                await queue.put(sse_data)
            except Exception as e:
                logger.warning(f"[ProgressStore] SSE 전송 실패: {e}")

    def start(self, project_id: str, agent_type: str) -> None:
        """에이전트 실행 시작"""
        # 기존 상태가 있으면 구독자 목록 보존 (race condition 방지)
        existing_subscribers: list[asyncio.Queue] = []
        if project_id in self._states:
            existing_subscribers = self._states[project_id].subscribers
            logger.info(f"[ProgressStore] 기존 구독자 {len(existing_subscribers)}명 보존: {project_id}")

        self._states[project_id] = ProgressState(
            project_id=project_id,
            agent_type=agent_type,
        )
        # 기존 구독자 복원
        self._states[project_id].subscribers = existing_subscribers

        logger.info(f"[ProgressStore] 에이전트 시작: {agent_type}, 구독자: {len(existing_subscribers)}명")

        # agent_start 이벤트 브로드캐스트
        event = AgentProgressEvent(
            event_type="agent_start",
            agent_type=agent_type,
            progress=0,
            message="분석을 시작합니다...",
            completed_nodes=[],
        )
        asyncio.create_task(self._broadcast(project_id, event))

    def update_node(
        self,
        project_id: str,
        node_id: str,
        event_type: Literal["node_start", "node_end"],
    ) -> None:
        """노드 진행 상태 업데이트"""
        state = self._states.get(project_id)
        if not state:
            logger.warning(f"[ProgressStore] 진행 상태 없음: {project_id}")
            return

        logger.info(f"[ProgressStore] 노드 업데이트: {node_id} ({event_type}), 구독자: {len(state.subscribers)}명")

        if event_type == "node_start":
            state.current_node = node_id
        elif event_type == "node_end":
            if node_id not in state.completed_nodes:
                state.completed_nodes.append(node_id)
            state.current_node = None

        # 진행률 계산
        state.progress = calculate_progress(state.agent_type, state.completed_nodes)
        node_label = get_node_label(state.agent_type, node_id)

        # 메시지 설정
        if event_type == "node_start":
            state.message = f"{node_label} 진행 중..."
        else:
            state.message = f"{node_label} 완료"

        # 이벤트 브로드캐스트
        event = AgentProgressEvent(
            event_type=event_type,
            agent_type=state.agent_type,
            node_id=node_id,
            node_label=node_label,
            progress=state.progress,
            message=state.message,
            completed_nodes=state.completed_nodes.copy(),
        )
        asyncio.create_task(self._broadcast(project_id, event))

    def end(self, project_id: str, error: str | None = None) -> None:
        """에이전트 실행 종료"""
        state = self._states.get(project_id)
        if not state:
            return

        state.is_complete = True
        state.current_node = None

        if error:
            state.error = error
            event = AgentProgressEvent(
                event_type="error",
                agent_type=state.agent_type,
                progress=state.progress,
                message=f"오류가 발생했습니다: {error}",
                completed_nodes=state.completed_nodes.copy(),
            )
        else:
            state.progress = 100
            event = AgentProgressEvent(
                event_type="agent_end",
                agent_type=state.agent_type,
                progress=100,
                message="분석이 완료되었습니다.",
                completed_nodes=state.completed_nodes.copy(),
            )

        asyncio.create_task(self._broadcast(project_id, event))

        # 잠시 후 상태 정리 (구독자들이 마지막 이벤트를 받을 시간 확보)
        asyncio.create_task(self._cleanup_after_delay(project_id, delay=5.0))

    async def _cleanup_after_delay(self, project_id: str, delay: float) -> None:
        """일정 시간 후 상태 정리"""
        await asyncio.sleep(delay)
        if project_id in self._states:
            del self._states[project_id]

    async def subscribe(self, project_id: str) -> AsyncGenerator[str, None]:
        """진행 상태 SSE 구독

        Args:
            project_id: 프로젝트 ID

        Yields:
            SSE 형식의 이벤트 문자열
        """
        queue: asyncio.Queue = asyncio.Queue()

        # 현재 상태가 있으면 구독자 등록
        state = self._states.get(project_id)
        if state:
            state.subscribers.append(queue)
            logger.info(f"[ProgressStore] 구독자 등록 (기존 상태): {project_id}, 총 {len(state.subscribers)}명, is_complete={state.is_complete}")

            # 현재 상태 즉시 전송 (이미 진행 중인 경우, 완료된 상태는 전송하지 않음)
            # 완료된 상태를 전송하면 새 에이전트 시작 전에 progress=100이 표시됨
            if not state.is_complete and (state.completed_nodes or state.current_node):
                fallback_node_id = state.current_node or (state.completed_nodes[-1] if state.completed_nodes else "")
                current_event = AgentProgressEvent(
                    event_type="node_start" if state.current_node else "node_end",
                    agent_type=state.agent_type,
                    node_id=state.current_node or (state.completed_nodes[-1] if state.completed_nodes else None),
                    node_label=get_node_label(state.agent_type, fallback_node_id),
                    progress=state.progress,
                    message=state.message,
                    completed_nodes=state.completed_nodes.copy(),
                )
                yield self._format_sse(current_event)
        else:
            # 상태가 없으면 대기 (에이전트 시작 전에 구독한 경우)
            # 새 상태가 생성될 때까지 빈 상태로 대기
            temp_state = ProgressState(project_id=project_id, agent_type="")
            temp_state.subscribers.append(queue)
            self._states[project_id] = temp_state
            logger.info(f"[ProgressStore] 구독자 등록 (대기 상태): {project_id}")

        try:
            while True:
                try:
                    # 타임아웃 설정 (연결 유지를 위한 heartbeat)
                    sse_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield sse_data

                    # agent_end 또는 error 이벤트면 종료
                    if '"event_type": "agent_end"' in sse_data or '"event_type": "error"' in sse_data:
                        break
                except asyncio.TimeoutError:
                    # heartbeat (연결 유지)
                    yield ": heartbeat\n\n"
        finally:
            # 구독 해제
            state = self._states.get(project_id)
            if state and queue in state.subscribers:
                state.subscribers.remove(queue)

    def get_state(self, project_id: str) -> ProgressState | None:
        """현재 진행 상태 조회"""
        return self._states.get(project_id)


# 싱글톤 인스턴스
progress_store = ProgressStore()
