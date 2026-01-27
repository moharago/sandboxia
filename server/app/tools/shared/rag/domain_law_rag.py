"""R3. 도메인별 규제·법령 RAG Tool

분야별 주요 법령/인허가 체계, 규제 쟁점 검색.

주 사용처: 1(서비스 구조화), 2(대상성 판단), 6(리스크 체크) 에이전트
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.db.vector import get_vectorstore


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
    vectorstore = get_vectorstore("domain_laws")

    # 도메인 정규화
    normalized_domain = normalize_domain(domain)

    # 검색 조건 설정
    search_kwargs = {"k": top_k}
    if normalized_domain:
        search_kwargs["filter"] = {"domain": normalized_domain}

    # 유사도 검색 (점수 포함)
    docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
        query,
        **search_kwargs,
    )

    results = []
    for doc, score in docs_with_scores:
        meta = doc.metadata
        results.append(
            DomainLawResult(
                content=doc.page_content,
                law_name=meta.get("law_name", ""),
                article_no=meta.get("article_no", ""),
                article_title=meta.get("article_title", ""),
                paragraph_no=meta.get("paragraph_no", ""),
                citation=meta.get("citation", ""),
                domain=meta.get("domain", ""),
                domain_label=meta.get("domain_label", ""),
                relevance_score=round(score, 4),
            )
        )

    return DomainLawSearchOutput(
        results=results,
        total_count=len(results),
        query=query,
        domain_filter=normalized_domain,
    )
