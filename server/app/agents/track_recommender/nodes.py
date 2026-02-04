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

    return {"track_scores": track_scores, "domain_constraints": domain_constraints}


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


def _format_track_definitions_for_prompt(track_definitions: list) -> str:
    """트랙 정의를 LLM이 인용하기 쉬운 형식으로 변환"""
    if not track_definitions:
        return "(검색 결과 없음)"

    lines = []
    for i, td in enumerate(track_definitions, 1):
        raw_source = td.get("source", "출처 미상")
        source = _clean_citation(raw_source) if raw_source != "출처 미상" else raw_source
        content = td.get("content", "")[:200]
        track_name = td.get("track_name", "")
        lines.append(f"{i}. [{source}] {track_name}: {content}...")

    return "\n".join(lines) if lines else "(검색 결과 없음)"


def _format_similar_cases_for_prompt(similar_cases: dict) -> str:
    """유사 사례를 LLM이 인용하기 쉬운 형식으로 변환"""
    if not similar_cases:
        return "(검색 결과 없음)"

    lines = []
    for track_key, cases in similar_cases.items():
        track_name_map = {"demo": "실증특례", "temp_permit": "임시허가", "quick_check": "신속확인"}
        track_name = track_name_map.get(track_key, track_key)

        if cases:
            lines.append(f"\n### {track_name} 유사 사례:")
            for case in cases:
                case_id = case.get("case_id", "")
                service_name = case.get("service_name", "")
                company_name = case.get("company_name", "")
                desc = case.get("service_description", "")[:100]
                lines.append(f"  - **{case_id}** ({company_name}): {service_name}")
                if desc:
                    lines.append(f"    설명: {desc}...")
        else:
            lines.append(f"\n### {track_name} 유사 사례: 없음")

    return "\n".join(lines) if lines else "(검색 결과 없음)"


# R1 RAG "카테고리" → 의미 있는 출처명 매핑
_CATEGORY_TO_SOURCE: dict[str, str] = {
    "트랙비교": "ICT 규제샌드박스 트랙 비교 가이드",
    "제도정의": "규제샌드박스 제도 정의",
    "절차": "규제샌드박스 신청 절차 가이드",
    "심사기준": "규제샌드박스 심사 기준",
    "요건": "규제샌드박스 신청 요건",
}


def _clean_citation(citation: str) -> str:
    """RAG citation을 의미 있는 출처명으로 정제

    R1 citation 형식: "카테고리 > 제목" (예: "트랙비교 > 병행 신청")
    → R1 RAG의 " > " 구분자는 항상 문서 섹션 헤더이므로 카테고리 기반 출처명으로 변환.
    (법령 인용은 「법명」 제N조 형식이며 " > " 구분자를 사용하지 않음.)
    """
    if not citation:
        return ""

    # " > " 구분자가 있으면 R1 RAG 섹션 헤더 → 카테고리 기반 출처명으로 변환
    if " > " in citation:
        category = citation.split(" > ", 1)[0].strip()
        return _CATEGORY_TO_SOURCE.get(category, f"규제샌드박스 {category} 가이드")

    # 일반 citation: 길이만 제한
    if len(citation) > 50:
        return citation[:50]

    return citation


def _extract_evidence_sources(
    track_definitions: list,
    similar_cases: dict,
    domain_constraints: dict | None = None,
) -> dict:
    """RAG 결과에서 실제 출처 목록 추출 (R1 + R2 + R3)"""
    sources = {
        "사례": [],
        "법령": [],
        "규제": [],
    }

    # R2: 유사 사례에서 case_id 추출 (중복 제거)
    seen_case_ids = set()
    for track_key, cases in similar_cases.items():
        for case in cases:
            case_id = case.get("case_id", "")
            if case_id and case_id not in seen_case_ids:
                sources["사례"].append(case_id)
                seen_case_ids.add(case_id)

    # R1: 트랙 정의에서 출처 추출 (중복 제거, citation 정제)
    seen_sources = set()
    for td in track_definitions:
        raw_source = td.get("source", "")
        if not raw_source:
            continue
        source = _clean_citation(raw_source)
        if not source or source in seen_sources:
            continue
        seen_sources.add(source)
        if any(kw in source for kw in ["법", "조", "규정", "시행령", "시행규칙"]):
            sources["법령"].append(source)
        else:
            sources["규제"].append(source)

    # R3: 도메인 법령에서 citation 추출 (구체적 법령 조항 보존)
    if domain_constraints:
        for constraint in domain_constraints.get("constraints", []):
            citation = constraint.get("source", "")
            law_name = constraint.get("law_name", "")
            # citation이 있으면 사용, 없으면 law_name 사용
            source = citation or law_name
            if not source or source in seen_sources:
                continue
            # R3 법령 citation은 _clean_citation 거치지 않고 직접 사용
            # (예: "의료법 제34조 제1항" → 그대로 보존)
            # 단, RAG 내부 경로(" > " 형식)만 정제
            if " > " in source:
                source = _clean_citation(source)
                if not source or source in seen_sources:
                    continue
            seen_sources.add(source)
            sources["법령"].append(source)

    # RAG에서 출처를 못 찾으면 비워둠 (generic 라벨로 대체하지 않음)
    # LLM에게 "추가 확인 필요"를 사용하도록 프롬프트에서 안내

    return sources


def _build_available_sources_text(
    track_definitions: list,
    similar_cases: dict,
    domain_constraints: dict | None = None,
) -> str:
    """LLM 프롬프트에 주입할 '사용 가능한 출처 목록' 텍스트 생성

    R2 사례: case_id + service_name 포함하여 LLM이 구체적으로 인용할 수 있게 함
    R3 법령: 구체적 citation 그대로 전달
    빈 목록: "추가 확인 필요" 사용 안내
    """
    sources = _extract_evidence_sources(
        track_definitions, similar_cases, domain_constraints
    )

    # R2 사례: case_id에 service_name을 병기하여 더 구체적으로 표시
    case_display = {}
    for track_key, cases in similar_cases.items():
        for case in cases:
            case_id = case.get("case_id", "")
            service_name = case.get("service_name", "")
            if case_id and case_id not in case_display:
                case_display[case_id] = service_name

    lines = []

    lines.append("### source_type: \"사례\" → 아래에서 선택")
    if sources["사례"]:
        for s in sources["사례"]:
            display_name = case_display.get(s, "")
            if display_name:
                lines.append(f"- {s} ({display_name})")
            else:
                lines.append(f"- {s}")
    else:
        lines.append("- (해당 사례 없음 — 출처가 필요하면 \"추가 확인 필요\" 사용)")

    lines.append("")
    lines.append("### source_type: \"법령\" → 아래에서 선택")
    if sources["법령"]:
        for s in sources["법령"]:
            lines.append(f"- {s}")
    else:
        lines.append("- (해당 법령 없음 — 출처가 필요하면 \"추가 확인 필요\" 사용)")

    lines.append("")
    lines.append("### source_type: \"규제\" → 아래에서 선택")
    if sources["규제"]:
        for s in sources["규제"]:
            lines.append(f"- {s}")
    else:
        lines.append("- (해당 규제 없음 — 출처가 필요하면 \"추가 확인 필요\" 사용)")

    return "\n".join(lines)


def _fix_evidence_sources(
    recommendation_data: dict,
    track_definitions: list,
    similar_cases: dict,
    domain_constraints: dict | None = None,
) -> dict:
    """LLM 응답의 evidence.source 검증 및 중복 제거

    1. RAG 내부 경로(" > " 형식)만 의미 있는 출처명으로 교체
    2. "추가 확인 필요"는 그대로 통과
    3. 유효 목록이 비어있으면 교체 시도 안 함
    4. 트랙 내 중복 source → 다른 출처로 교체
    """
    sources = _extract_evidence_sources(
        track_definitions, similar_cases, domain_constraints
    )

    # 유효한 출처 집합 생성
    valid_sources = set()
    for source_list in sources.values():
        valid_sources.update(source_list)

    # 전체 출처 풀 (source_type별 + 통합)
    all_sources = sources.get("사례", []) + sources.get("법령", []) + sources.get("규제", [])

    for track_key in ["demo", "temp_permit", "quick_check"]:
        track_data = recommendation_data.get(track_key, {})
        evidence_list = track_data.get("evidence", [])

        # 1단계: RAG 내부 경로만 정제, LLM이 생성한 구체적 출처는 보존
        for i, ev in enumerate(evidence_list):
            if not isinstance(ev, dict):
                continue

            current_source = ev.get("source", "")

            # "추가 확인 필요"는 그대로 통과
            if current_source == "추가 확인 필요":
                continue

            # RAG 내부 경로(" > " 형식)는 정제
            if " > " in current_source:
                ev["source"] = _clean_citation(current_source)
                continue

            # 유효 목록이 비어있으면 LLM 출처를 그대로 유지
            if not valid_sources:
                continue

            # 유효 목록에 있으면 통과
            if current_source in valid_sources:
                continue

            # 유효 목록에 없는 경우: source_type별 fallback이 있을 때만 교체
            source_type = ev.get("source_type", "규제")
            fallback = sources.get(source_type, [])
            if fallback:
                ev["source"] = fallback[i % len(fallback)]
            # fallback이 없으면 LLM이 생성한 출처를 그대로 유지

        # 2단계: 트랙 내 중복 source 제거
        used_sources = set()
        for ev in evidence_list:
            if not isinstance(ev, dict):
                continue

            current_source = ev.get("source", "")
            if current_source in used_sources:
                # 중복 → 아직 사용하지 않은 다른 출처로 교체
                source_type = ev.get("source_type", "규제")
                candidates = sources.get(source_type, []) + all_sources
                replaced = False
                for candidate in candidates:
                    if candidate not in used_sources:
                        ev["source"] = candidate
                        used_sources.add(candidate)
                        replaced = True
                        break
                if not replaced:
                    # 모든 출처를 사용한 경우 그대로 유지
                    used_sources.add(current_source)
            else:
                used_sources.add(current_source)

    return recommendation_data


def generate_recommendation_node(state: TrackRecommenderState) -> dict:
    """추천 사유 및 근거 생성 노드"""
    canonical = state.get("canonical", {})
    track_scores = state.get("track_scores", {})
    track_definitions = state.get("track_definitions", [])
    similar_cases = state.get("similar_cases", {})
    domain_constraints = state.get("domain_constraints", {})

    service_info = extract_service_info(canonical)

    # RAG 결과를 LLM이 인용하기 쉬운 형식으로 변환
    formatted_definitions = _format_track_definitions_for_prompt(track_definitions)
    formatted_cases = _format_similar_cases_for_prompt(similar_cases)

    # 사용 가능한 출처 목록 생성 (R1 + R2 + R3)
    available_sources = _build_available_sources_text(
        track_definitions, similar_cases, domain_constraints
    )

    # LLM 호출
    llm = get_llm()
    prompt = RECOMMENDATION_USER_PROMPT.format(
        service_info=service_info,
        track_scores=json.dumps(track_scores, ensure_ascii=False, indent=2),
        track_definitions=formatted_definitions,
        similar_cases=formatted_cases,
        available_sources=available_sources,
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

    # evidence.source 후처리: 유효하지 않은 출처를 RAG 출처로 교체
    recommendation_data = _fix_evidence_sources(
        recommendation_data, track_definitions, similar_cases, domain_constraints
    )

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

    # evidence.source 최종 정제: RAG 섹션 헤더("카테고리 > 제목") → 의미 있는 출처명
    for track_key in track_comparison:
        for ev in track_comparison[track_key].get("evidence", []):
            if isinstance(ev, dict):
                src = ev.get("source", "")
                if " > " in src:
                    ev["source"] = _clean_citation(src)

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
