"""Service Structurer Agent 상태 정의

에이전트 실행 중 공유되는 상태를 TypedDict로 정의합니다.
"""

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ServiceStructurerState(TypedDict):
    """Service Structurer Agent 상태

    Attributes:
        messages: 대화 메시지 히스토리
        session_id: 세션 ID
        requested_track: 요청된 트랙 (counseling/fastcheck/temporary/demonstration)
        consultant_input: 컨설턴트 입력 데이터
        hwp_parse_results: HWP 파싱 결과 리스트
        canonical_structure: 최종 Canonical Structure
        error: 에러 메시지 (있는 경우)
    """

    # 메시지 히스토리 (LangGraph 메시지 누적)
    messages: Annotated[list, add_messages]

    # 입력 데이터
    session_id: str
    requested_track: str
    consultant_input: dict[str, Any]  # 컨설턴트가 입력한 데이터
    file_paths: list[str]  # HWP 파일 경로 리스트
    file_subtypes: list[str]  # 각 파일의 서브타입

    # 중간 처리 결과
    hwp_parse_results: list[dict[str, Any]]  # HWP 파싱 결과

    # 최종 출력
    canonical_structure: dict[str, Any] | None  # Canonical Structure JSON

    # 에러 처리
    error: str | None


class ConsultantInput(TypedDict, total=False):
    """컨설턴트 입력 데이터 구조

    클라이언트에서 전달받는 컨설턴트 입력 데이터입니다.
    모든 필드는 optional입니다.
    """

    company_name: str
    representative: str
    service_name: str
    service_description: str
    memo: str
