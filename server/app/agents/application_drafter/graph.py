"""Application Drafter Agent LangGraph 정의

워크플로우:
1. load_form_schema: 트랙에 맞는 폼 스키마 로드
2. retrieve_context: R1/R2/R3 RAG 검색으로 컨텍스트 수집
3. generate_draft: form_schema를 템플릿으로 canonical 기반 값 생성
"""

import time

from langgraph.graph import END, StateGraph

from app.agents.application_drafter.nodes import (
    generate_draft_node,
    load_form_schema_node,
    retrieve_context_node,
)
from app.agents.application_drafter.state import ApplicationDrafterState


def build_application_drafter_graph() -> StateGraph:
    """Application Drafter Agent 그래프 생성"""
    graph = StateGraph(ApplicationDrafterState)

    # 노드 추가
    graph.add_node("load_form_schema", load_form_schema_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_draft", generate_draft_node)

    # 엣지 정의
    graph.set_entry_point("load_form_schema")
    graph.add_edge("load_form_schema", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_draft")
    graph.add_edge("generate_draft", END)

    return graph.compile()


# 싱글톤 인스턴스
application_drafter_agent = build_application_drafter_graph()


async def run_application_drafter(
    project_id: str,
    canonical: dict,
    track: str,
) -> dict:
    """Application Drafter Agent 실행

    Args:
        project_id: 프로젝트 UUID
        canonical: 프로젝트의 canonical 데이터
        track: 선택된 트랙 ("demo" | "temp_permit" | "quick_check")

    Returns:
        application_draft 딕셔너리
    """
    total_start = time.time()
    print("\n[Step4] ========== 신청서 초안 생성 시작 ==========")

    initial_state: ApplicationDrafterState = {
        "project_id": project_id,
        "canonical": canonical,
        "track": track,
        "form_schema": {},
        "application_requirements": [],
        "review_criteria": [],
        "similar_cases": [],
        "domain_laws": [],
        "application_draft": {},
        "model_name": "",
    }

    result = await application_drafter_agent.ainvoke(
        initial_state,
        config={"recursion_limit": 15},
    )

    total_elapsed = time.time() - total_start
    print(f"[Step4] ========== 신청서 초안 생성 완료 ({total_elapsed:.2f}초) ==========\n")

    return {
        "project_id": project_id,
        "application_draft": result.get("application_draft", {}),
        "model_name": result.get("model_name", ""),
        "similar_cases": result.get("similar_cases", []),
        "domain_laws": result.get("domain_laws", []),
    }
