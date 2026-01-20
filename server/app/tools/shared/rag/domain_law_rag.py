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
    """
    Search major statutory provisions with an optional domain filter and return structured, relevance-ranked results.
    
    Performs a domain-filtered retrieval over a curated vector store of statutes and regulations and returns matched provisions with metadata and a relevance score.
    
    Parameters:
        query (str): Search query describing the legal issue or phrase.
        domain (str | None): Optional domain filter; accepts standardized codes (e.g., "healthcare", "finance", "data", "privacy", "telecom") or common Korean labels (e.g., "의료", "금융", "데이터", "개인정보", "통신"). If None or empty, no domain filtering is applied.
        top_k (int): Maximum number of results to return.
    
    Returns:
        DomainLawSearchOutput: Object containing the list of matched DomainLawResult entries (each with content, citation, domain metadata, and a relevance_score), the total result count, the original query, and the applied normalized domain filter (or None).
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