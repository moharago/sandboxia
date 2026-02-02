"""Eligibility Evaluator LangGraph 워크플로우

노드들을 연결하여 대상성 판단 파이프라인 구성
"""

from langgraph.graph import END, StateGraph

from .nodes import (
    compose_decision_node,
    generate_evidence_node,
    screen_node,
    search_cases_node,
    search_laws_node,
    search_regulations_node,
)
from .schemas import EligibilityResult, EvidenceData
from .state import EligibilityState


def create_eligibility_graph() -> StateGraph:
    """Eligibility Evaluator 그래프 생성

    워크플로우:
    1. screen: 규제 스크리닝 (키워드/도메인 탐지)
    2. search_regulations: R1 규제제도 검색
    3. search_cases: R2 승인 사례 검색
    4. search_laws: R3 도메인별 법령 검색
    5. compose_decision: 최종 판정 통합
    6. generate_evidence: 근거 데이터 생성

    Returns:
        컴파일된 StateGraph
    """
    # 그래프 생성 (BaseModel State 사용)
    graph = StateGraph(EligibilityState)

    # 노드 추가
    graph.add_node("screen", screen_node)
    graph.add_node("search_regulations", search_regulations_node)
    graph.add_node("search_cases", search_cases_node)
    graph.add_node("search_laws", search_laws_node)
    graph.add_node("compose_decision", compose_decision_node)
    graph.add_node("generate_evidence", generate_evidence_node)

    # 엣지 연결
    # 1. 시작 → 스크리닝
    graph.set_entry_point("screen")

    # 2. 스크리닝 → 병렬 검색 (순차 실행으로 단순화)
    graph.add_edge("screen", "search_regulations")
    graph.add_edge("search_regulations", "search_cases")
    graph.add_edge("search_cases", "search_laws")

    # 3. 검색 완료 → 판정 통합
    graph.add_edge("search_laws", "compose_decision")

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
    )
