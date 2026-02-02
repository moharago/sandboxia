"""Track Recommender Agent 노드 함수"""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from app.agents.track_recommender.prompts import (
    RECOMMENDATION_SYSTEM_PROMPT,
    RECOMMENDATION_USER_PROMPT,
)
from app.agents.track_recommender.state import TrackRecommenderState
from app.agents.track_recommender.tools import (
    calculate_ranks_and_status,
    retrieve_domain_constraints,
    retrieve_similar_cases,
    retrieve_track_definitions,
    score_track,
)
from app.core.config import settings
from app.tools.shared.rag import (
    compare_tracks,
    search_domain_law,
)


def _camel_to_snake(name: str) -> str:
    """camelCase를 snake_case로 변환"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _normalize_keys(obj: Any) -> Any:
    """딕셔너리 키를 snake_case로 정규화 (재귀적)"""
    if isinstance(obj, dict):
        return {_camel_to_snake(k): _normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_keys(item) for item in obj]
    return obj


def get_field(data: dict, snake_key: str, camel_key: str, default: Any = None) -> Any:
    """snake_case와 camelCase 키를 모두 지원하여 값 반환

    Args:
        data: 조회할 딕셔너리
        snake_key: snake_case 키 (우선)
        camel_key: camelCase 키 (대체)
        default: 기본값

    Returns:
        찾은 값 또는 기본값
    """
    return data.get(snake_key) or data.get(camel_key) or default


def get_llm():
    """LLM 인스턴스 생성"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.1,
        api_key=settings.OPENAI_API_KEY,
    )


def extract_service_info(canonical: dict) -> str:
    """Canonical 구조에서 서비스 정보 추출 (snake_case/camelCase 모두 지원)"""
    if not canonical:
        return "(서비스 정보 없음)"

    parts = []

    # 회사 정보 (company / companyInfo)
    company = canonical.get("company") or canonical.get("companyInfo") or {}
    company_name = get_field(company, "company_name", "companyName")
    if company_name:
        parts.append(f"회사명: {company_name}")

    # 서비스 정보 (service / serviceInfo)
    service = canonical.get("service") or canonical.get("serviceInfo") or {}
    service_name = get_field(service, "service_name", "serviceName")
    service_description = get_field(service, "service_description", "serviceDescription")
    target_users = get_field(service, "target_users", "targetUsers")

    if service_name:
        parts.append(f"서비스명: {service_name}")
    if service_description:
        parts.append(f"서비스 설명: {service_description}")
    if target_users:
        parts.append(f"대상 사용자: {target_users}")

    # 기술 정보 (technology / technologyInfo)
    technology = canonical.get("technology") or canonical.get("technologyInfo") or {}
    core_technology = get_field(technology, "core_technology", "coreTechnology")
    innovation_points = get_field(technology, "innovation_points", "innovationPoints", [])

    if core_technology:
        parts.append(f"핵심 기술: {core_technology}")
    if innovation_points:
        if isinstance(innovation_points, list):
            parts.append(f"혁신 포인트: {', '.join(innovation_points)}")
        else:
            parts.append(f"혁신 포인트: {innovation_points}")

    # 규제 정보 (regulatory / regulatoryInfo)
    regulatory = canonical.get("regulatory") or canonical.get("regulatoryInfo") or {}
    regulatory_issues = get_field(regulatory, "regulatory_issues", "regulatoryIssues", [])
    related_regulations = get_field(regulatory, "related_regulations", "relatedRegulations", [])

    if regulatory_issues:
        if isinstance(regulatory_issues, list):
            issues_text = ", ".join(
                issue.get("summary", str(issue)) if isinstance(issue, dict) else str(issue)
                for issue in regulatory_issues
            )
            parts.append(f"규제 쟁점: {issues_text}")
        else:
            parts.append(f"규제 쟁점: {regulatory_issues}")
    if related_regulations:
        if isinstance(related_regulations, list):
            parts.append(f"관련 규제: {', '.join(related_regulations)}")
        else:
            parts.append(f"관련 규제: {related_regulations}")

    return "\n".join(parts) if parts else "(서비스 정보 없음)"


def _build_combined_context(
    canonical: dict,
    similar_cases: dict,
) -> str:
    """R1(트랙 정의), R2(유사 사례), R3(도메인 규제) 컨텍스트 통합 생성"""
    context_parts = []

    # R1: 트랙 비교 정보 조회
    try:
        track_comparison_results = compare_tracks.invoke({})
        if track_comparison_results:
            r1_texts = [r.content for r in track_comparison_results[:3]]
            context_parts.append(
                "[R1. 트랙 정의/요건]\n" + "\n".join(r1_texts)
            )
    except Exception:
        pass  # RAG 실패 시 무시

    # R3: 도메인 규제 조회 (canonical의 관련 규제 기반)
    regulatory = canonical.get("regulatory") or canonical.get("regulatoryInfo") or {}
    related_regulations = get_field(
        regulatory, "related_regulations", "relatedRegulations", []
    )
    if related_regulations:
        try:
            # 관련 규제를 쿼리로 사용하여 도메인 법령 검색
            query = ", ".join(related_regulations) if isinstance(related_regulations, list) else str(related_regulations)
            domain_law_results = search_domain_law.invoke({"query": query, "top_k": 3})
            if domain_law_results:
                r3_texts = [r.content for r in domain_law_results[:3]]
                context_parts.append(
                    "[R3. 도메인 규제/법령]\n" + "\n".join(r3_texts)
                )
        except Exception:
            pass  # RAG 실패 시 무시

    # R2: 유사 사례 요약 (이미 조회된 결과 활용)
    r2_parts = []
    for track_key, cases in similar_cases.items():
        if cases:
            case_names = [c.get("service_name", "이름 없음") for c in cases[:3]]
            r2_parts.append(f"- {track_key}: {len(cases)}건 ({', '.join(case_names)})")
    if r2_parts:
        context_parts.append(
            "[R2. 유사 승인 사례]\n" + "\n".join(r2_parts)
        )

    return "\n\n".join(context_parts)


def score_all_tracks_node(state: TrackRecommenderState) -> dict:
    """모든 트랙의 적합도 점수 계산 노드 (R1/R2/R3 컨텍스트 포함)"""
    canonical = state.get("canonical", {})
    similar_cases = state.get("similar_cases", {})  # R2 RAG 검색 결과 참조
    service_info = extract_service_info(canonical)

    # 컨설턴트 메모 추출 (snake_case/camelCase 모두 지원)
    metadata = canonical.get("metadata") or canonical.get("additionalInfo") or {}
    consultant_memo = get_field(metadata, "consultant_memo", "consultantMemo", "")

    # R3: 도메인 규제 제약사항 조회
    regulatory = canonical.get("regulatory") or canonical.get("regulatoryInfo") or {}
    related_regulations = get_field(
        regulatory, "related_regulations", "relatedRegulations", []
    )
    domain_constraints = retrieve_domain_constraints.invoke({
        "related_regulations": related_regulations if isinstance(related_regulations, list) else [related_regulations] if related_regulations else [],
        "service_description": service_info[:200],
        "top_k": 5,
    })

    # R1/R2/R3 통합 컨텍스트 생성
    combined_context = _build_combined_context(canonical, similar_cases)

    # 컨설턴트 메모와 통합 컨텍스트 결합
    additional_notes = consultant_memo
    if combined_context:
        additional_notes += f"\n\n{combined_context}"

    # R3 차단 규제가 있으면 컨텍스트에 추가
    if domain_constraints.get("has_blocking_issue"):
        blocking_info = "\n\n[⚠️ R3. 차단 규제 감지]\n"
        for reg in domain_constraints.get("blocking_regulations", [])[:3]:
            blocking_info += f"- {reg.get('source', '출처 미상')}: {reg.get('content', '')[:100]}...\n"
        additional_notes += blocking_info

    track_keys = ["demo", "temp_permit", "quick_check"]
    track_scores = {}

    for track_key in track_keys:
        result = score_track.invoke({
            "track_key": track_key,
            "service_info": service_info,
            "additional_notes": additional_notes,
        })
        track_scores[track_key] = result

    # 순위 및 상태 계산 (R3 도메인 제약 반영)
    track_scores = calculate_ranks_and_status(track_scores, domain_constraints)

    return {"track_scores": track_scores}


def retrieve_definitions_node(state: TrackRecommenderState) -> dict:
    """트랙 정의/요건 RAG 검색 노드"""
    track_keys = ["demo", "temp_permit", "quick_check"]

    definitions = retrieve_track_definitions.invoke({
        "track_keys": track_keys,
    })

    return {"track_definitions": definitions}


def retrieve_cases_node(state: TrackRecommenderState) -> dict:
    """유사 승인 사례 RAG 검색 노드"""
    canonical = state.get("canonical", {})

    # service 또는 serviceInfo에서 서비스 설명 추출 (snake_case/camelCase 모두 지원)
    service = canonical.get("service") or canonical.get("serviceInfo") or {}
    service_description = get_field(service, "service_description", "serviceDescription", "")

    if not service_description:
        service_description = extract_service_info(canonical)

    track_keys = ["demo", "temp_permit", "quick_check"]

    similar_cases = retrieve_similar_cases.invoke({
        "service_description": service_description,
        "track_keys": track_keys,
        "top_k": 3,
    })

    return {"similar_cases": similar_cases}


def generate_recommendation_node(state: TrackRecommenderState) -> dict:
    """추천 사유 및 근거 생성 노드"""
    canonical = state.get("canonical", {})
    track_scores = state.get("track_scores", {})
    track_definitions = state.get("track_definitions", [])
    similar_cases = state.get("similar_cases", {})

    service_info = extract_service_info(canonical)

    # LLM 호출
    llm = get_llm()
    prompt = RECOMMENDATION_USER_PROMPT.format(
        service_info=service_info,
        track_scores=json.dumps(track_scores, ensure_ascii=False, indent=2),
        track_definitions=json.dumps(track_definitions, ensure_ascii=False, indent=2),
        similar_cases=json.dumps(similar_cases, ensure_ascii=False, indent=2),
    )

    response = llm.invoke([
        {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    # JSON 파싱
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        recommendation_data = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        # 파싱 실패 시 기본값
        recommendation_data = {
            "demo": {"reasons": [], "evidence": []},
            "temp_permit": {"reasons": [], "evidence": []},
            "quick_check": {"reasons": [], "evidence": []},
            "result_summary": "추천 사유 생성에 실패했습니다.",
        }

    # track_comparison 구조 생성
    track_comparison = {}
    for track_key in ["demo", "temp_permit", "quick_check"]:
        score_data = track_scores.get(track_key, {})
        rec_data = recommendation_data.get(track_key, {})

        track_comparison[track_key] = {
            "fit_score": score_data.get("fit_score", 0),
            "rank": score_data.get("rank", 3),
            "status": score_data.get("status", "비추천"),
            "reasons": rec_data.get("reasons", []),
            "evidence": rec_data.get("evidence", []),
        }

    # 1순위 트랙 찾기
    recommended_track = "demo"
    for track_key, data in track_comparison.items():
        if data["rank"] == 1:
            recommended_track = track_key
            break

    # 신뢰도 = 1순위 트랙의 fit_score
    confidence_score = track_comparison[recommended_track]["fit_score"]

    return {
        "recommended_track": recommended_track,
        "confidence_score": confidence_score,
        "result_summary": recommendation_data.get("result_summary", ""),
        "track_comparison": track_comparison,
    }
