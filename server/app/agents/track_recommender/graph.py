"""Track Recommender Agent LangGraph 정의

워크플로우:
1. retrieve_cases: 유사 승인 사례 RAG 검색 (R2) - 먼저 실행
2. score_all_tracks: 3개 트랙 점수 계산 (LLM 체크리스트) - 유사 사례 정보 참조
3. retrieve_definitions: 트랙 정의/요건 RAG 검색 (R1)
4. generate_recommendation: 추천 사유 및 근거 생성 (LLM)
"""

from langgraph.graph import END, StateGraph

from app.agents.track_recommender.nodes import (
    generate_recommendation_node,
    retrieve_cases_node,
    retrieve_definitions_node,
    score_all_tracks_node,
)
from app.agents.track_recommender.state import TrackRecommenderState


def build_track_recommender_graph() -> StateGraph:
    """Track Recommender Agent 그래프 생성"""
    graph = StateGraph(TrackRecommenderState)

    # 노드 추가
    graph.add_node("score_all_tracks", score_all_tracks_node)
    graph.add_node("retrieve_definitions", retrieve_definitions_node)
    graph.add_node("retrieve_cases", retrieve_cases_node)
    graph.add_node("generate_recommendation", generate_recommendation_node)

    # 엣지 정의
    # 시작 → 유사 사례 검색 (먼저 실행하여 similar_cases_exist 기준 판단에 활용)
    graph.set_entry_point("retrieve_cases")

    # 사례 검색 → 점수 계산 (유사 사례 정보 참조)
    graph.add_edge("retrieve_cases", "score_all_tracks")

    # 점수 계산 → 정의/요건 검색
    graph.add_edge("score_all_tracks", "retrieve_definitions")

    # 검색 완료 → 추천 생성
    graph.add_edge("retrieve_definitions", "generate_recommendation")

    # 추천 생성 → 종료
    graph.add_edge("generate_recommendation", END)

    return graph.compile()


# 싱글톤 인스턴스
track_recommender_agent = build_track_recommender_graph()


async def run_track_recommender(
    project_id: str,
    canonical: dict,
) -> dict:
    """Track Recommender Agent 실행

    Args:
        project_id: 프로젝트 UUID
        canonical: 프로젝트의 canonical 데이터

    Returns:
        추천 결과 딕셔너리
    """
    from app.agents.utils import run_agent_with_progress

    initial_state: TrackRecommenderState = {
        "project_id": project_id,
        "canonical": canonical,
        "track_scores": {},
        "track_definitions": [],
        "similar_cases": {},
        "domain_constraints": {},
        "recommended_track": "",
        "confidence_score": 0.0,
        "result_summary": "",
        "track_comparison": {},
    }

    # 에이전트 실행 (진행 상태 추적 포함)
    result = await run_agent_with_progress(
        agent=track_recommender_agent,
        initial_state=initial_state,
        project_id=project_id,
        agent_type="track_recommender",
    )

    return {
        "project_id": project_id,
        "recommended_track": result["recommended_track"],
        "confidence_score": result["confidence_score"],
        "result_summary": result["result_summary"],
        "track_comparison": result["track_comparison"],
        "similar_cases": result.get("similar_cases", []),
        "domain_constraints": result.get("domain_constraints", []),
    }
