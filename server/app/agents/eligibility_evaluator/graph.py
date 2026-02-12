"""Eligibility Evaluator LangGraph 워크플로우

노드들을 연결하여 대상성 판단 파이프라인 구성
"""

import time

from langgraph.graph import END, StateGraph

from app.core.config import settings

from .nodes import (
    compose_decision_node,
    generate_evidence_node,
    screen_node,
    search_all_rag_node,
)
from .schemas import EligibilityResult, EvidenceData
from .state import EligibilityState


def create_eligibility_graph() -> StateGraph:
    """Eligibility Evaluator 그래프 생성

    워크플로우:
    1. screen: 규제 스크리닝 (키워드/도메인 탐지)
    2. search_all_rag: R1+R2+R3 병렬 검색
    3. compose_decision: 최종 판정 통합
    4. generate_evidence: 근거 데이터 생성 (LLM 병렬)

    Returns:
        컴파일된 StateGraph
    """
    # 그래프 생성 (BaseModel State 사용)
    graph = StateGraph(EligibilityState)

    # 노드 추가
    graph.add_node("screen", screen_node)
    graph.add_node("search_all_rag", search_all_rag_node)
    graph.add_node("compose_decision", compose_decision_node)
    graph.add_node("generate_evidence", generate_evidence_node)

    # 엣지 연결
    # 1. 시작 → 스크리닝
    graph.set_entry_point("screen")

    # 2. 스크리닝 → RAG 병렬 검색
    graph.add_edge("screen", "search_all_rag")

    # 3. 검색 완료 → 판정 통합
    graph.add_edge("search_all_rag", "compose_decision")

    # 4. 판정 → 근거 생성
    graph.add_edge("compose_decision", "generate_evidence")

    # 5. 근거 생성 → 종료
    graph.add_edge("generate_evidence", END)

    return graph


def compile_eligibility_graph():
    """컴파일된 그래프 반환"""
    graph = create_eligibility_graph()
    return graph.compile()


# 컴파일된 그래프 인스턴스
eligibility_graph = compile_eligibility_graph()


async def run_eligibility_evaluation(
    project_id: str,
    canonical: dict,
) -> EligibilityResult:
    """대상성 판단 실행

    Args:
        project_id: 프로젝트 UUID
        canonical: 서비스 정보 (projects.canonical)

    Returns:
        EligibilityResult: 판단 결과
    """
    total_start = time.time()
    print("\n[Step2] ========== 대상성 판단 시작 ==========")

    # 초기 상태 (TypedDict - 기본값 직접 제공)
    initial_state: EligibilityState = {
        "project_id": project_id,
        "canonical": canonical,
        # 중간 결과 (기본값)
        "screening_result": None,
        "regulation_results": [],
        "case_results": [],
        "law_results": [],
        # 최종 출력 (기본값)
        "eligibility_label": None,
        "confidence_score": None,
        "result_summary": None,
        "direct_launch_risks": [],
        "judgment_summary": [],
        "approval_cases": [],
        "regulations": [],
    }

    # 그래프 실행 (recursion_limit: 무한 루프 방지)
    result = await eligibility_graph.ainvoke(
        initial_state,
        config={"recursion_limit": 15},
    )

    total_elapsed = time.time() - total_start
    print(f"[Step2] ========== 대상성 판단 완료 ({total_elapsed:.2f}초) ==========\n")

    # EligibilityResult로 변환 (result는 dict)
    return EligibilityResult(
        eligibility_label=result["eligibility_label"],
        confidence_score=result.get("confidence_score") or 0.0,
        result_summary=result.get("result_summary") or "",
        direct_launch_risks=result.get("direct_launch_risks", []),
        evidence_data=EvidenceData(
            judgment_summary=result.get("judgment_summary", []),
            approval_cases=result.get("approval_cases", []),
            regulations=result.get("regulations", []),
        ),
        model_name=settings.LLM_MODEL,
    )
