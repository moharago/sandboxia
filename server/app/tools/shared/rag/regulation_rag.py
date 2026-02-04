"""R1. 규제제도 & 절차 RAG Tool (ICT 규제샌드박스 특화)

제도 정의(신속확인/실증특례/임시허가), 절차, 제출 요건, 심사 포인트 검색.
ICT 규제샌드박스(과학기술정보통신부) 관련 정보만 제공합니다.

주 사용처: 2(대상성 판단), 3(트랙 추천), 4(신청서 작성), 6(체크리스트) 에이전트
"""

from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.constants import COLLECTION_REGULATIONS
from app.db.vector import SearchResult, get_vector_store

# 관련도 임계값: 이 값 미만의 결과는 반환하지 않음
RELEVANCE_THRESHOLD = 0.32


class RegulationResult(BaseModel):
    """규제제도 검색 결과"""

    content: str = Field(description="내용")
    document_title: str = Field(description="문서 제목")
    section_title: str = Field(description="섹션 제목")
    track: str = Field(description="트랙 (신속확인/실증특례/임시허가/all)")
    category: str = Field(description="카테고리 코드")
    category_label: str = Field(description="카테고리 한글명")
    ministry: str = Field(description="관련 부처")
    citation: str = Field(description="인용 형식")
    source_url: str | None = Field(default=None, description="원본 문서 URL")
    relevance_score: float = Field(description="관련도 점수")


class RegulationSearchOutput(BaseModel):
    """규제제도 검색 출력"""

    results: list[RegulationResult] = Field(description="검색 결과 목록")
    total_count: int = Field(description="총 결과 수")
    query: str = Field(description="검색 쿼리")
    track_filter: str | None = Field(description="적용된 트랙 필터")
    category_filter: str | None = Field(description="적용된 카테고리 필터")
    ministry_filter: str | None = Field(description="적용된 부처 필터")


# 트랙 정규화 매핑
TRACK_MAPPING = {
    "신속확인": "신속확인",
    "신속": "신속확인",
    "rapid": "신속확인",
    "실증특례": "실증특례",
    "실증": "실증특례",
    "demonstration": "실증특례",
    "임시허가": "임시허가",
    "임시": "임시허가",
    "temporary": "임시허가",
}

# 카테고리 정규화 매핑
CATEGORY_MAPPING = {
    "개요": "overview",
    "overview": "overview",
    "정의": "definition",
    "definition": "definition",
    "트랙": "definition",
    "절차": "procedure",
    "procedure": "procedure",
    "신청": "procedure",
    "요건": "requirement",
    "서류": "requirement",
    "requirement": "requirement",
    "심사": "criteria",
    "기준": "criteria",
    "criteria": "criteria",
    "비교": "comparison",
    "comparison": "comparison",
    "부처": "ministry",
    "ministry": "ministry",
    "개선": "changes",
    "변경": "changes",
    "changes": "changes",
}

# 부처 정규화 매핑
MINISTRY_MAPPING = {
    "산업부": "산업통상자원부",
    "산업통상자원부": "산업통상자원부",
    "과기부": "과학기술정보통신부",
    "과학기술정보통신부": "과학기술정보통신부",
    "금융위": "금융위원회",
    "금융위원회": "금융위원회",
    "중기부": "중소벤처기업부",
    "중소벤처기업부": "중소벤처기업부",
    "국토부": "국토교통부",
    "국토교통부": "국토교통부",
    "환경부": "환경부",
}


def normalize_track(track: str | None) -> str | None:
    """트랙 입력을 정규화"""
    if not track:
        return None
    track_lower = track.lower().strip()
    return TRACK_MAPPING.get(track_lower, TRACK_MAPPING.get(track, None))


def normalize_category(category: str | None) -> str | None:
    """카테고리 입력을 정규화"""
    if not category:
        return None
    category_lower = category.lower().strip()
    return CATEGORY_MAPPING.get(category_lower, CATEGORY_MAPPING.get(category, None))


def normalize_ministry(ministry: str | None) -> str | None:
    """부처 입력을 정규화"""
    if not ministry:
        return None
    return MINISTRY_MAPPING.get(ministry, None)


def _build_filter(
    track: str | None = None,
    category: str | None = None,
    ministry: str | None = None,
) -> dict[str, Any] | None:
    """필터 조건 구성"""
    filter_conditions = []

    if track:
        # track이 특정 값이거나 "all"인 경우 모두 포함
        filter_conditions.append(
            {
                "$or": [
                    {"track": {"$eq": track}},
                    {"track": {"$eq": "all"}},
                ]
            }
        )

    if category:
        filter_conditions.append({"category": {"$eq": category}})

    if ministry:
        filter_conditions.append(
            {
                "$or": [
                    {"ministry": {"$eq": ministry}},
                    {"ministry": {"$eq": "all"}},
                ]
            }
        )

    if not filter_conditions:
        return None

    if len(filter_conditions) == 1:
        return filter_conditions[0]

    return {"$and": filter_conditions}


def _build_regulation_result(result: SearchResult, score_override: float | None = None) -> RegulationResult:
    """SearchResult를 RegulationResult로 변환"""
    meta = result.metadata
    return RegulationResult(
        content=result.content,
        document_title=meta.get("document_title", ""),
        section_title=meta.get("section_title", ""),
        track=meta.get("track", "all"),
        category=meta.get("category", ""),
        category_label=meta.get("category_label", ""),
        ministry=meta.get("ministry", "all"),
        citation=meta.get("citation", ""),
        source_url=meta.get("source_url"),
        relevance_score=round(score_override if score_override is not None else result.score, 4),
    )


@tool
def search_regulation(
    query: str,
    track: str | None = None,
    category: str | None = None,
    ministry: str | None = None,
    top_k: int = 5,
) -> RegulationSearchOutput:
    """R1. 규제제도 & 절차 RAG 검색

    규제샌드박스 제도 정의, 절차, 요건, 심사기준을 검색합니다.

    Args:
        query: 검색 쿼리 (예: "신속확인 신청 절차", "실증특례 제출 서류")
        track: 트랙 필터 (신속확인, 실증특례, 임시허가)
        category: 카테고리 필터 (overview, definition, procedure, requirement, criteria, comparison, ministry, changes)
        ministry: 부처 필터 (산업통상자원부, 과학기술정보통신부, 금융위원회 등)
        top_k: 반환할 결과 수 (기본값: 5)

    Returns:
        관련 규제제도 정보 리스트 (출처 정보 포함)

    Example:
        >>> search_regulation("신속확인 신청 기간")
        >>> search_regulation("제출 서류", track="실증특례")
        >>> search_regulation("심사 기준", category="criteria")
        >>> search_regulation("ICT 규제샌드박스", ministry="과기부")
    """
    vector_store = get_vector_store(COLLECTION_REGULATIONS)

    # 필터 정규화
    normalized_track = normalize_track(track)
    normalized_category = normalize_category(category)
    normalized_ministry = normalize_ministry(ministry)

    # 필터 조건 구성
    filter_dict = _build_filter(
        track=normalized_track,
        category=normalized_category,
        ministry=normalized_ministry,
    )

    # 유사도 검색 (추상화된 인터페이스 사용)
    search_results = vector_store.similarity_search(
        query=query,
        k=top_k,
        filter=filter_dict,
    )

    results = []
    for result in search_results:
        # 관련도 임계값 미만인 결과는 제외
        if result.score < RELEVANCE_THRESHOLD:
            continue

        results.append(_build_regulation_result(result))

    return RegulationSearchOutput(
        results=results,
        total_count=len(results),
        query=query,
        track_filter=normalized_track,
        category_filter=normalized_category,
        ministry_filter=normalized_ministry,
    )


@tool
def get_track_definition(track: str) -> list[RegulationResult]:
    """특정 트랙의 정의 및 상세 정보 조회

    Args:
        track: 트랙명 (신속확인, 실증특례, 임시허가)

    Returns:
        해당 트랙의 정의 및 관련 정보 리스트
    """
    vector_store = get_vector_store(COLLECTION_REGULATIONS)

    normalized_track = normalize_track(track)
    if not normalized_track:
        return []

    # 필터 구성
    filter_dict = {
        "$and": [
            {"category": {"$eq": "definition"}},
            {
                "$or": [
                    {"track": {"$eq": normalized_track}},
                    {"track": {"$eq": "all"}},
                ]
            },
        ]
    }

    # 트랙 정의 문서 검색
    search_results = vector_store.similarity_search(
        query=f"{normalized_track} 정의 요건 절차",
        k=10,
        filter=filter_dict,
    )

    if not search_results:
        return []

    return [_build_regulation_result(result, score_override=1.0) for result in search_results]


@tool
def get_application_requirements(track: str | None = None) -> list[RegulationResult]:
    """신청 요건 및 제출 서류 조회

    Args:
        track: 트랙명 (신속확인, 실증특례, 임시허가) - 없으면 전체

    Returns:
        신청 요건 및 제출 서류 정보 리스트
    """
    vector_store = get_vector_store(COLLECTION_REGULATIONS)

    normalized_track = normalize_track(track)

    # 필터 구성
    if normalized_track:
        filter_dict: dict[str, Any] = {
            "$and": [
                {"category": {"$eq": "requirement"}},
                {
                    "$or": [
                        {"track": {"$eq": normalized_track}},
                        {"track": {"$eq": "all"}},
                    ]
                },
            ]
        }
    else:
        filter_dict = {"category": {"$eq": "requirement"}}

    search_results = vector_store.similarity_search(
        query=f"신청 요건 제출 서류 {track or ''}",
        k=10,
        filter=filter_dict,
    )

    if not search_results:
        return []

    return [_build_regulation_result(result, score_override=1.0) for result in search_results]


@tool
def get_review_criteria(track: str | None = None) -> list[RegulationResult]:
    """심사 기준 조회

    Args:
        track: 트랙명 (신속확인, 실증특례, 임시허가) - 없으면 전체

    Returns:
        심사 기준 정보 리스트
    """
    vector_store = get_vector_store(COLLECTION_REGULATIONS)

    normalized_track = normalize_track(track)

    # 필터 구성
    if normalized_track:
        filter_dict: dict[str, Any] = {
            "$and": [
                {"category": {"$eq": "criteria"}},
                {
                    "$or": [
                        {"track": {"$eq": normalized_track}},
                        {"track": {"$eq": "all"}},
                    ]
                },
            ]
        }
    else:
        filter_dict = {"category": {"$eq": "criteria"}}

    search_results = vector_store.similarity_search(
        query=f"심사 기준 평가 항목 {track or ''}",
        k=10,
        filter=filter_dict,
    )

    if not search_results:
        return []

    return [_build_regulation_result(result, score_override=1.0) for result in search_results]


@tool
def compare_tracks() -> list[RegulationResult]:
    """트랙 비교 정보 조회 (신속확인 vs 실증특례 vs 임시허가)

    Returns:
        트랙 비교 정보 리스트
    """
    vector_store = get_vector_store(COLLECTION_REGULATIONS)

    search_results = vector_store.similarity_search(
        query="신속확인 실증특례 임시허가 비교 차이점",
        k=10,
        filter={"category": {"$eq": "comparison"}},
    )

    if not search_results:
        return []

    return [_build_regulation_result(result, score_override=1.0) for result in search_results]


@tool
def list_available_tracks() -> dict:
    """사용 가능한 트랙 및 카테고리 목록 조회

    Returns:
        트랙 및 카테고리 목록
    """
    return {
        "tracks": {
            "신속확인": "규제 존재 여부 확인 (30일 이내)",
            "실증특례": "시험·검증을 위한 규제 면제 (2년, 연장 가능)",
            "임시허가": "시장 출시를 위한 임시 허가 (2년, 연장 가능)",
        },
        "categories": {
            "overview": "제도 개요",
            "definition": "트랙 정의",
            "procedure": "신청 절차",
            "requirement": "제출 서류",
            "criteria": "심사 기준",
            "comparison": "트랙 비교",
            "ministry": "부처별 차이",
            "changes": "제도 개선",
        },
        "ministries": {
            "산업통상자원부": "산업융합 규제샌드박스",
            "과학기술정보통신부": "ICT 규제샌드박스",
            "금융위원회": "금융 규제샌드박스 (혁신금융서비스)",
            "중소벤처기업부": "규제자유특구",
            "국토교통부": "스마트도시/모빌리티 규제샌드박스",
            "환경부": "순환경제 규제샌드박스",
        },
    }
