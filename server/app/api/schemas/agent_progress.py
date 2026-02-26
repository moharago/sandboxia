"""에이전트 진행 상태 스키마

각 에이전트의 노드 정보와 진행 상태를 정의합니다.
프론트엔드에서 로딩 화면에 단계별 진행 상태를 표시할 때 사용됩니다.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    """노드 실행 상태"""
    PENDING = "pending"      # 대기 중
    RUNNING = "running"      # 실행 중
    COMPLETED = "completed"  # 완료
    ERROR = "error"          # 에러


class NodeInfo(BaseModel):
    """노드 정보"""
    id: str = Field(..., description="노드 ID")
    label: str = Field(..., description="노드 라벨 (한글)")
    description: str = Field(..., description="노드 설명")


class NodeProgress(BaseModel):
    """노드 진행 상태"""
    node_id: str = Field(..., description="노드 ID")
    status: NodeStatus = Field(..., description="노드 상태")
    message: str | None = Field(None, description="추가 메시지")


class AgentProgressEvent(BaseModel):
    """에이전트 진행 이벤트 (SSE로 전송)"""
    event_type: Literal["node_start", "node_end", "agent_start", "agent_end", "error"]
    agent_type: str = Field(..., description="에이전트 타입")
    node_id: str | None = Field(None, description="현재 노드 ID")
    node_label: str | None = Field(None, description="현재 노드 라벨")
    progress: int = Field(..., ge=0, le=100, description="진행률 (0-100)")
    message: str | None = Field(None, description="진행 메시지")
    completed_nodes: list[str] = Field(default_factory=list, description="완료된 노드 ID 목록")


# ===============================
# 에이전트별 노드 정의
# ===============================

# 노드 정보: (노드 ID, 라벨, 설명)
AGENT_NODES: dict[str, list[NodeInfo]] = {
    "service_structurer": [
        NodeInfo(id="parse_hwp", label="파일 분석", description="HWP 파일을 파싱하고 내용을 추출합니다"),
        NodeInfo(id="build_structure", label="구조화", description="서비스 정보를 표준 구조로 변환합니다"),
    ],
    "eligibility_evaluator": [
        NodeInfo(id="screen", label="규제 탐지", description="규제 저촉 신호를 탐지합니다"),
        NodeInfo(id="search_all_rag", label="자료 검색", description="관련 규제, 사례, 법령을 검색합니다"),
        NodeInfo(id="compose_decision", label="판정 생성", description="대상성 판정을 생성합니다"),
        NodeInfo(id="generate_evidence", label="근거 생성", description="판단 근거를 정리합니다"),
    ],
    "track_recommender": [
        NodeInfo(id="retrieve_cases", label="사례 검색", description="유사 승인 사례를 검색합니다"),
        NodeInfo(id="score_all_tracks", label="트랙 평가", description="각 트랙의 적합도를 평가합니다"),
        NodeInfo(id="retrieve_definitions", label="정의 검색", description="트랙 정의와 요건을 검색합니다"),
        NodeInfo(id="generate_recommendation", label="추천 생성", description="최적의 트랙을 추천합니다"),
    ],
    "application_drafter": [
        NodeInfo(id="load_form_schema", label="양식 로드", description="트랙에 맞는 신청서 양식을 로드합니다"),
        NodeInfo(id="retrieve_context", label="자료 검색", description="작성에 필요한 참고 자료를 검색합니다"),
        NodeInfo(id="generate_draft", label="초안 생성", description="신청서 초안을 생성합니다"),
    ],
    "strategy_advisor": [
        NodeInfo(id="retrieve_cases", label="사례 검색", description="유사 승인 사례를 검색합니다"),
        NodeInfo(id="extract_patterns", label="패턴 추출", description="승인 포인트 패턴을 추출합니다"),
        NodeInfo(id="generate_strategy", label="전략 생성", description="적용 전략을 생성합니다"),
    ],
    "risk_checker": [
        NodeInfo(id="generate_checklist", label="체크리스트 생성", description="기준 체크리스트를 생성합니다"),
        NodeInfo(id="detect_gaps", label="누락 탐지", description="누락/약점을 탐지합니다"),
        NodeInfo(id="generate_report", label="리포트 생성", description="최종 검수 리포트를 생성합니다"),
    ],
}


def get_agent_nodes(agent_type: str) -> list[NodeInfo]:
    """에이전트의 노드 목록 반환 (방어적 복사)"""
    return list(AGENT_NODES.get(agent_type, []))


def get_node_label(agent_type: str, node_id: str) -> str:
    """노드 ID로 라벨 조회"""
    nodes = AGENT_NODES.get(agent_type, [])
    for node in nodes:
        if node.id == node_id:
            return node.label
    return node_id


def calculate_progress(agent_type: str, completed_nodes: list[str]) -> int:
    """완료된 노드 수 기반 진행률 계산 (중복 제거 및 유효 노드만 계산)"""
    agent_node_ids = {node.id for node in AGENT_NODES.get(agent_type, [])}
    total_nodes = len(agent_node_ids)
    if total_nodes == 0:
        return 0
    # 중복 제거 및 유효한 노드만 카운트
    valid_completed = set(completed_nodes) & agent_node_ids
    progress = int((len(valid_completed) / total_nodes) * 100)
    return min(progress, 100)  # 최대 100으로 제한
