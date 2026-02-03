"""Track Recommender Agent Tools

A. 트랙 적합도 스코어링 (LLM 체크리스트)
B. 트랙 정의/요건 RAG (R1)
C. 유사 트랙 승인 사례 RAG (R2)
D. 도메인 규제/법령 RAG (R3)
E. 추천 사유 생성 (LLM)
"""

import json

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.agents.track_recommender.prompts import (
    SCORING_SYSTEM_PROMPT,
    SCORING_USER_PROMPT,
    TRACK_CRITERIA,
)
from app.core.config import settings
from app.tools.shared.rag import (
    compare_tracks,
    get_track_definition,
    search_case,
    search_domain_law,
)


def get_llm():
    """LLM 인스턴스 생성"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,
    )


@tool
def score_track(
    track_key: str,
    service_info: str,
    additional_notes: str = "",
) -> dict:
    """트랙 적합도 스코어링 (LLM 체크리스트 방식)

    Args:
        track_key: 트랙 키 ("demo" | "temp_permit" | "quick_check")
        service_info: 서비스 정보 텍스트
        additional_notes: 컨설턴트 추가 메모

    Returns:
        점수 및 체크리스트 결과
    """
    if track_key not in TRACK_CRITERIA:
        return {"error": f"Invalid track_key: {track_key}"}

    track_info = TRACK_CRITERIA[track_key]
    criteria = track_info["criteria"]

    # 체크리스트 질문 생성
    criteria_questions = "\n".join([
        f"### {i+1}. {c['question']}\n- 설명: {c['description']}\n- ID: {c['id']}"
        for i, c in enumerate(criteria)
    ])

    # LLM 호출
    llm = get_llm()
    prompt = SCORING_USER_PROMPT.format(
        service_info=service_info,
        additional_notes=additional_notes or "(없음)",
        track_name=track_info["name"],
        criteria_questions=criteria_questions,
    )

    response = llm.invoke([
        {"role": "system", "content": SCORING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    # JSON 파싱
    try:
        # 응답에서 JSON 추출
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        criteria_results = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        # 파싱 실패 시 기본값
        criteria_results = {c["id"]: {"answer": False, "reason": "파싱 실패"} for c in criteria}

    # 점수 계산 (충족된 기준 수 / 전체 기준 수 × 100)
    total_criteria = len(criteria)
    matched_criteria = sum(
        1 for c in criteria
        if criteria_results.get(c["id"], {}).get("answer", False)
    )
    fit_score = int((matched_criteria / total_criteria) * 100)

    return {
        "track_key": track_key,
        "track_name": track_info["name"],
        "fit_score": fit_score,
        "matched_count": matched_criteria,
        "total_count": total_criteria,
        "criteria_results": criteria_results,
    }


@tool
def retrieve_track_definitions(track_keys: list[str]) -> list[dict]:
    """트랙 정의/요건 RAG 검색 (R1)

    Args:
        track_keys: 검색할 트랙 키 목록

    Returns:
        트랙별 정의/요건 정보
    """
    results = []

    # 트랙 비교 정보 검색 (.invoke() 메서드 사용)
    comparison_results = compare_tracks.invoke({})
    if comparison_results:
        for r in comparison_results:
            results.append({
                "type": "comparison",
                "content": r.content,
                "source": r.citation,
            })

    # 각 트랙별 정의 검색
    track_name_map = {
        "demo": "실증특례",
        "temp_permit": "임시허가",
        "quick_check": "신속확인",
    }

    for track_key in track_keys:
        track_name = track_name_map.get(track_key)
        if not track_name:
            continue

        definition_results = get_track_definition.invoke({"track": track_name})
        if definition_results:
            for r in definition_results[:3]:  # 상위 3개만
                results.append({
                    "type": "definition",
                    "track": track_key,
                    "track_name": track_name,
                    "content": r.content,
                    "source": r.citation,
                })

    return results


@tool
def retrieve_similar_cases(
    service_description: str,
    track_keys: list[str],
    top_k: int = 3,
) -> dict[str, list[dict]]:
    """트랙별 유사 승인 사례 RAG 검색 (R2)

    Args:
        service_description: 서비스 설명
        track_keys: 검색할 트랙 키 목록
        top_k: 트랙별 반환할 사례 수

    Returns:
        트랙별 유사 사례 목록
    """
    track_name_map = {
        "demo": "실증특례",
        "temp_permit": "임시허가",
        "quick_check": "신속확인",
    }

    results = {}

    for track_key in track_keys:
        track_name = track_name_map.get(track_key)
        if not track_name:
            results[track_key] = []
            continue

        # R2 RAG 검색 (.invoke() 메서드 사용)
        search_result = search_case.invoke({
            "query": service_description,
            "track": track_name,
            "top_k": top_k,
            "deduplicate": True,
        })

        cases = []
        if search_result and search_result.results:
            for case in search_result.results:
                cases.append({
                    "case_id": case.case_id,
                    "company_name": case.company_name,
                    "service_name": case.service_name,
                    "track": case.track,
                    "service_description": case.service_description[:200] if case.service_description else "",
                    "special_provisions": case.special_provisions[:200] if case.special_provisions else "",
                    "relevance_score": case.relevance_score,
                })

        results[track_key] = cases

    return results


@tool
def retrieve_domain_constraints(
    related_regulations: list[str],
    service_description: str = "",
    top_k: int = 5,
) -> dict:
    """도메인 규제/법령 RAG 검색 (R3)

    canonical의 관련 규제 목록 또는 서비스 설명을 쿼리로 사용하여
    도메인별 법령/규제를 검색합니다.

    Args:
        related_regulations: 관련 규제 목록 (canonical.regulatory.related_regulations)
        service_description: 서비스 설명 (related_regulations가 없을 때 대체 쿼리)
        top_k: 반환할 결과 수

    Returns:
        도메인 규제 정보 및 제약사항
    """
    results = {
        "constraints": [],
        "blocking_regulations": [],
        "has_blocking_issue": False,
    }

    # 쿼리 구성: related_regulations 우선, 없으면 service_description 사용
    query_parts = []
    if related_regulations:
        query_parts.append(
            ", ".join(related_regulations) if isinstance(related_regulations, list)
            else str(related_regulations)
        )
    if service_description:
        query_parts.append(service_description[:200])

    if not query_parts:
        return results

    query = " ".join(query_parts)

    try:
        domain_results = search_domain_law.invoke({"query": query, "top_k": top_k})
        if domain_results:
            for r in domain_results:
                constraint = {
                    "content": r.content,
                    "source": getattr(r, "citation", ""),
                    "law_name": getattr(r, "law_name", ""),
                }
                results["constraints"].append(constraint)

                # 차단 규제 감지 (키워드 기반)
                content_lower = r.content.lower() if r.content else ""
                blocking_keywords = ["금지", "불가", "위반", "처벌", "벌금", "불허"]
                if any(kw in content_lower for kw in blocking_keywords):
                    results["blocking_regulations"].append(constraint)
                    results["has_blocking_issue"] = True

    except Exception:
        pass  # RAG 실패 시 빈 결과 반환

    return results


def calculate_ranks_and_status(
    track_scores: dict,
    domain_constraints: dict | None = None,
) -> dict:
    """점수 기반으로 순위와 상태 계산 (R3 도메인 제약 반영)

    Args:
        track_scores: 트랙별 점수 딕셔너리
        domain_constraints: 도메인 규제 제약사항 (R3 결과)

    Returns:
        순위와 상태가 추가된 트랙 점수
    """
    # R3 도메인 제약에 따른 점수 조정
    if domain_constraints and domain_constraints.get("has_blocking_issue"):
        blocking_regs = domain_constraints.get("blocking_regulations", [])
        penalty = min(len(blocking_regs) * 10, 30)  # 최대 30점 페널티

        for track_key, score_data in track_scores.items():
            original_score = score_data.get("fit_score", 0)
            adjusted_score = max(0, original_score - penalty)
            score_data["fit_score"] = adjusted_score
            score_data["domain_penalty"] = penalty
            score_data["blocking_regulations"] = [
                reg.get("source", "") for reg in blocking_regs
            ]

    # 점수 기준 정렬
    sorted_tracks = sorted(
        track_scores.items(),
        key=lambda x: x[1]["fit_score"],
        reverse=True
    )

    # 순위 및 상태 할당
    for rank, (track_key, score_data) in enumerate(sorted_tracks, start=1):
        score_data["rank"] = rank
        fit_score = score_data["fit_score"]

        # 상태 결정 (도메인 차단 규제가 있으면 추가 경고)
        has_blocking = score_data.get("domain_penalty", 0) > 0

        if rank == 1 and fit_score >= 70:
            score_data["status"] = "AI 추천 (규제 주의)" if has_blocking else "AI 추천"
        elif fit_score >= 50:
            score_data["status"] = "조건부 가능 (규제 확인 필요)" if has_blocking else "조건부 가능"
        else:
            score_data["status"] = "비추천"

    return track_scores
