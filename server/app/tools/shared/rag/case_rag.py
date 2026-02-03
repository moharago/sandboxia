"""R2. 승인 사례 RAG Tool

승인/반려 사례, 조건/부대조건, 실증 범위, 안전·책임, 소비자 고지, 적용 특례 검색.

주 사용처: 2(유사 사례 존재), 5(전략 패턴 추출), 6(리스크/보완 포인트), (보조로 4 초안 문장 근거)
"""

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.db.vector import get_vector_store

# 데이터 경로
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "r2"
CASES_JSON_PATH = DATA_DIR / "cases_structured.json"


class CaseResult(BaseModel):
    """승인 사례 검색 결과"""

    case_id: str = Field(description="사례 고유 ID")
    company_name: str = Field(description="신청 기업명")
    all_companies: list[str] = Field(description="컨소시엄 전체 기업 목록")
    service_name: str = Field(description="서비스명")
    track: str = Field(description="트랙 (실증특례/임시허가)")
    designation_number: str = Field(description="지정번호")
    service_description: str = Field(description="서비스 설명")
    current_regulation: str = Field(description="현행 규제")
    special_provisions: str = Field(description="특례 내용")
    conditions: list[str] = Field(description="부가 조건")
    pilot_scope: str = Field(description="실증 범위")
    expected_effect: str = Field(description="기대 효과")
    review_result: str = Field(description="심의 결과")
    relevance_score: float | None = Field(description="관련도 점수")
    source_url: str | None = Field(description="원본 문서 URL")


class CaseSearchOutput(BaseModel):
    """승인 사례 검색 출력"""

    results: list[CaseResult] = Field(description="검색 결과 목록")
    total_count: int = Field(description="총 결과 수")
    query: str = Field(description="검색 쿼리")
    track_filter: str | None = Field(description="적용된 트랙 필터")


class SimilarCaseReference(BaseModel):
    """신청서 작성 참고용 유사 사례"""

    similar_cases: list[CaseResult] = Field(description="유사 사례 목록")
    recommended_points: list[dict[str, str]] = Field(description="추천 포인트")
    common_conditions: list[str] = Field(description="공통 조건")


# 전역 캐시
_cases_data: dict[str, Any] | None = None


def _load_cases_data() -> dict[str, Any]:
    """JSON 데이터 로드 (캐싱)"""
    global _cases_data
    if _cases_data is None:
        if not CASES_JSON_PATH.exists():
            raise FileNotFoundError(f"사례 데이터 파일을 찾을 수 없습니다: {CASES_JSON_PATH}")
        with open(CASES_JSON_PATH, encoding="utf-8") as f:
            cases = json.load(f)
            _cases_data = {c["case_id"]: c for c in cases}
    return _cases_data


def _build_case_result(
    case_id: str,
    company_name: str = "",
    score: float | None = None,
    meta: dict | None = None,
) -> CaseResult:
    """케이스 결과 객체 생성"""
    cases_data = _load_cases_data()
    case = cases_data.get(case_id, {})
    common = case.get("common_info", {})
    companies = case.get("companies", [])

    all_companies = [c.get("company_name", "") for c in companies if c.get("company_name")]
    if not all_companies and company_name:
        all_companies = [company_name]

    return CaseResult(
        case_id=case_id,
        company_name=company_name or (all_companies[0] if all_companies else ""),
        all_companies=all_companies,
        service_name=meta.get("service_name", "") if meta else common.get("service_name", ""),
        track=meta.get("track", "") if meta else case.get("track", ""),
        designation_number=meta.get("designation_number", "") if meta else "",
        service_description=common.get("service_description", ""),
        current_regulation=common.get("current_regulation", ""),
        special_provisions=common.get("special_provisions", ""),
        conditions=common.get("conditions", []),
        pilot_scope=common.get("pilot_scope", ""),
        expected_effect=common.get("expected_effect", ""),
        review_result=common.get("review_result", ""),
        relevance_score=round(score, 4) if score is not None else None,
        source_url=case.get("source_url"),
    )


def _deduplicate_results(results: list[CaseResult]) -> list[CaseResult]:
    """같은 case_id 결과 중복 제거"""
    seen_cases: dict[str, CaseResult] = {}

    for r in results:
        if r.case_id not in seen_cases:
            seen_cases[r.case_id] = r
        else:
            # 이미 있는 케이스면 회사명 통합
            existing = seen_cases[r.case_id]
            if r.company_name and r.company_name not in existing.all_companies:
                existing.all_companies.append(r.company_name)

    return list(seen_cases.values())


@tool
def search_case(
    query: str,
    track: str | None = None,
    top_k: int = 5,
    deduplicate: bool = True,
) -> CaseSearchOutput:
    """R2. 승인 사례 RAG 검색

    규제샌드박스 승인/반려 사례를 검색합니다.
    서비스 설명, 규제 쟁점, 특례 내용 등으로 유사 사례를 찾습니다.

    Args:
        query: 검색 쿼리 (예: "자율주행 배달 로봇", "원격 의료 모니터링")
        track: 트랙 필터 (실증특례, 임시허가)
        top_k: 반환할 결과 수 (기본값: 5)
        deduplicate: 같은 케이스 중복 제거 여부 (기본값: True)

    Returns:
        유사 승인 사례 리스트 (조건, 특례, 범위 등 포함)

    Example:
        >>> search_case("AI 기반 건강 모니터링")
        >>> search_case("자율주행", track="실증특례")
    """
    vector_store = get_vector_store("r2_cases")

    # 중복 제거 고려해서 더 많이 검색
    fetch_count = top_k * 3 if deduplicate else top_k

    # 필터 조건
    filter_dict: dict[str, Any] | None = None
    if track:
        filter_dict = {"track": track}

    # 유사도 검색 (추상화된 인터페이스 사용)
    search_results = vector_store.similarity_search(
        query=query,
        k=fetch_count,
        filter=filter_dict,
    )

    results = []
    for result in search_results:
        meta = result.metadata
        case_id = meta.get("case_id", "")

        case_result = _build_case_result(
            case_id=case_id,
            company_name=meta.get("company_name", ""),
            score=result.score,
            meta=meta,
        )
        results.append(case_result)

    if deduplicate:
        results = _deduplicate_results(results)

    return CaseSearchOutput(
        results=results[:top_k],
        total_count=len(results[:top_k]),
        query=query,
        track_filter=track,
    )


@tool
def get_similar_cases_for_application(
    service_description: str,
    track: str | None = None,
    top_k: int = 5,
) -> SimilarCaseReference:
    """신청서 작성 시 참고할 유사 사례 및 포인트 추출

    서비스 설명을 기반으로 유사한 승인 사례를 찾고,
    신청서 작성에 참고할 수 있는 포인트와 공통 조건을 추출합니다.

    Args:
        service_description: 신청하려는 서비스 설명
        track: 트랙 필터 (실증특례, 임시허가)
        top_k: 반환할 유사 사례 수

    Returns:
        유사 사례, 추천 포인트, 공통 조건

    Example:
        >>> get_similar_cases_for_application("배달 로봇이 보도를 주행하며 음식을 배달하는 서비스")
    """
    # 유사 사례 검색
    search_result = search_case.invoke({
        "query": service_description,
        "track": track,
        "top_k": top_k,
        "deduplicate": True,
    })
    similar_cases = search_result.results

    # 공통 조건 추출
    from collections import Counter

    all_conditions = []
    for case in similar_cases:
        all_conditions.extend(case.conditions)

    condition_counts = Counter(all_conditions)
    common_conditions = [c for c, _ in condition_counts.most_common(10)]

    # 추천 포인트 생성
    recommended_points = []
    for case in similar_cases[:3]:
        point = {}
        if case.service_name:
            point["source"] = case.service_name[:50]
        if case.company_name:
            point["company"] = case.company_name
        if case.special_provisions:
            point["special_provisions"] = case.special_provisions[:300]
        if case.review_result:
            point["review_result"] = case.review_result[:300]
        if point:
            recommended_points.append(point)

    return SimilarCaseReference(
        similar_cases=similar_cases,
        recommended_points=recommended_points,
        common_conditions=common_conditions,
    )


@tool
def get_case_detail(case_id: str) -> CaseResult | None:
    """특정 케이스 상세 정보 조회

    Args:
        case_id: 사례 고유 ID

    Returns:
        케이스 상세 정보 (없으면 None)

    Example:
        >>> get_case_detail("실증특례_100_에이아이포펫")
    """
    cases_data = _load_cases_data()
    if case_id not in cases_data:
        return None

    return _build_case_result(case_id=case_id)


@tool
def get_approval_patterns(
    domain_keyword: str,
    track: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """도메인별 승인 패턴 추출 (전략 에이전트용)

    특정 도메인의 승인 사례에서 공통 패턴을 추출합니다.

    Args:
        domain_keyword: 도메인 키워드 (예: "헬스케어", "자율주행", "금융")
        track: 트랙 필터
        top_k: 분석할 사례 수

    Returns:
        승인 패턴 (공통 조건, 특례 유형, 실증 범위 패턴)

    Example:
        >>> get_approval_patterns("자율주행", track="실증특례")
    """
    search_result = search_case.invoke({
        "query": domain_keyword,
        "track": track,
        "top_k": top_k,
        "deduplicate": True,
    })
    cases = search_result.results

    from collections import Counter

    # 공통 조건 분석
    all_conditions = []
    for case in cases:
        all_conditions.extend(case.conditions)
    common_conditions = [c for c, _ in Counter(all_conditions).most_common(10)]

    # 특례 내용 수집
    special_provisions_samples = [
        case.special_provisions[:200] for case in cases if case.special_provisions
    ][:5]

    # 실증 범위 수집
    pilot_scope_samples = [
        case.pilot_scope[:200] for case in cases if case.pilot_scope
    ][:5]

    return {
        "domain": domain_keyword,
        "track_filter": track,
        "analyzed_cases": len(cases),
        "common_conditions": common_conditions,
        "special_provisions_samples": special_provisions_samples,
        "pilot_scope_samples": pilot_scope_samples,
    }


@tool
def list_available_tracks() -> dict[str, str]:
    """사용 가능한 트랙 목록 조회

    Returns:
        트랙 목록 및 설명
    """
    return {
        "실증특례": "시험·검증을 위한 규제 면제 (2년, 연장 가능)",
        "임시허가": "시장 출시를 위한 임시 허가 (2년, 연장 가능)",
    }
