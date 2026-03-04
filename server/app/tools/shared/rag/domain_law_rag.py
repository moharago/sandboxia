"""R3. 도메인별 규제·법령 RAG Tool

분야별 주요 법령/인허가 체계, 규제 쟁점 검색.

주 사용처: 1(서비스 구조화), 2(대상성 판단), 6(리스크 체크) 에이전트
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.constants import COLLECTION_LAWS
from app.db.vector import Eq, FilterExpr, SearchResult, get_vector_store


class DomainLawResult(BaseModel):
    """도메인 법령 검색 결과"""

    content: str = Field(description="조문 내용")
    law_name: str = Field(description="법령명")
    article_no: str = Field(description="조문번호")
    article_title: str = Field(description="조문제목")
    paragraph_no: str = Field(description="항번호 (①②③ 등)")
    citation: str = Field(description="인용 형식 (예: 의료법 제34조 제1항)")
    domain: str = Field(description="도메인 코드")
    domain_label: str = Field(description="도메인 한글명")
    source_url: str | None = Field(default=None, description="국가법령정보센터 URL")
    relevance_score: float = Field(description="관련도 점수")


class DomainLawSearchOutput(BaseModel):
    """도메인 법령 검색 출력"""

    results: list[DomainLawResult] = Field(description="검색 결과 목록")
    total_count: int = Field(description="총 결과 수")
    query: str = Field(description="검색 쿼리")
    domain_filter: str | None = Field(description="적용된 도메인 필터")


# 도메인 코드 매핑
DOMAIN_MAPPING = {
    "의료": "healthcare",
    "헬스케어": "healthcare",
    "healthcare": "healthcare",
    "금융": "finance",
    "핀테크": "finance",
    "finance": "finance",
    "데이터": "data",
    "data": "data",
    "개인정보": "privacy",
    "privacy": "privacy",
    "통신": "telecom",
    "ict": "telecom",
    "telecom": "telecom",
    "규제": "regulation",
    "제도": "regulation",
    "규제/제도": "regulation",
    "샌드박스": "regulation",
    "regulation": "regulation",
}


def normalize_domain(domain: str | None) -> str | None:
    """도메인 입력을 정규화"""
    if not domain:
        return None
    domain_lower = domain.lower().strip()
    return DOMAIN_MAPPING.get(domain_lower, domain_lower)


def _build_law_source_url(meta: dict) -> str | None:
    """메타데이터의 law_mst로 국가법령정보센터 URL 생성"""
    law_mst = meta.get("law_mst")
    if not law_mst:
        return None
    return f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={law_mst}"


def _build_domain_law_result(result: SearchResult) -> DomainLawResult:
    """SearchResult를 DomainLawResult로 변환"""
    meta = result.metadata
    return DomainLawResult(
        content=result.content,
        law_name=meta.get("law_name", ""),
        article_no=meta.get("article_no", ""),
        article_title=meta.get("article_title", ""),
        paragraph_no=meta.get("paragraph_no", ""),
        citation=meta.get("citation", ""),
        domain=meta.get("domain", ""),
        domain_label=meta.get("domain_label", ""),
        source_url=_build_law_source_url(meta),
        relevance_score=round(result.score, 4),
    )


@tool
def search_domain_law(
    query: str,
    domain: str | None = None,
    top_k: int = 5,
) -> DomainLawSearchOutput:
    """R3. 도메인별 규제·법령 RAG 검색

    분야별 주요 법령의 조문을 검색합니다.

    포함 법령:
    - 도메인별: 의료법, 전자금융거래법, 데이터기본법, 신용정보법, 개인정보보호법,
      전기통신사업법, 정보통신 진흥 및 융합 활성화 등에 관한 특별법
    - 규제/제도: 산업융합 촉진법, 금융혁신지원 특별법, 지역특구법, 행정규제기본법

    Args:
        query: 검색 쿼리 (예: "원격의료 허용 범위", "실증특례 신청 요건")
        domain: 도메인 필터 (healthcare, finance, data, privacy, telecom, regulation)
                또는 한글 (의료, 금융, 데이터, 개인정보, 통신, 규제/제도/샌드박스)
        top_k: 반환할 결과 수 (기본값: 5)

    Returns:
        관련 법령 조문 리스트 (출처 정보 포함)

    Example:
        >>> search_domain_law("비대면 진료", domain="의료")
        >>> search_domain_law("실증특례 허가 요건", domain="규제")
        >>> search_domain_law("개인신용정보 제3자 제공")
    """
    vector_store = get_vector_store(COLLECTION_LAWS)

    # 도메인 정규화
    normalized_domain = normalize_domain(domain)

    # 필터 조건 설정
    filter_expr: FilterExpr | None = None
    if normalized_domain:
        filter_expr = Eq("domain", normalized_domain)

    # Hybrid Search (E1 + H3: Dense 70% + Sparse 30%)
    search_results = vector_store.hybrid_search(
        query=query,
        k=top_k,
        filter=filter_expr,
    )

    results = [_build_domain_law_result(result) for result in search_results]

    # DEBUG: 에이전트 실행 중 RAG 검색 결과 확인
    print(f"\n{'='*60}")
    print(f"[R3 도메인법령 RAG] query='{query}', domain={normalized_domain}, top_k={top_k}")
    print(f"{'='*60}")
    for i, r in enumerate(results, 1):
        print(f"{'-'*60}")
        print(f"  {i}. [{r.citation}] (점수: {r.relevance_score})")
        print(f"     도메인: {r.domain_label}")
        print(f"     내용: {r.content[:150]}...")
    print(f"{'='*60}\n")

    return DomainLawSearchOutput(
        results=results,
        total_count=len(results),
        query=query,
        domain_filter=normalized_domain,
    )
