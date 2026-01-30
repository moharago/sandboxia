"""Service Structurer Agent

HWP 문서와 컨설턴트 입력을 분석하여
표준화된 서비스 구조(Canonical Structure)를 생성하는 에이전트입니다.

사용법:
    from app.agents.service_structurer import run_service_structurer

    result = await run_service_structurer(
        session_id="session_123",
        requested_track="counseling",
        consultant_input={
            "company_name": "테스트 회사",
            "service_name": "AI 서비스",
            "service_description": "AI 기반 서비스 설명",
        },
        file_paths=["/path/to/document.hwp"],
        file_subtypes=["counseling-1"],
    )
"""

from app.agents.service_structurer.graph import (
    run_service_structurer,
    service_structurer_agent,
)
from app.agents.service_structurer.state import (
    ConsultantInput,
    ServiceStructurerState,
)

__all__ = [
    "service_structurer_agent",
    "run_service_structurer",
    "ServiceStructurerState",
    "ConsultantInput",
]
