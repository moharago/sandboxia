"""법령정보 API 클라이언트 서비스"""

import httpx
from pydantic import BaseModel

from app.core.config import settings


class LawSummary(BaseModel):
    """법령 목록 요약 정보"""

    law_id: str  # 법령ID
    mst: str  # 법령일련번호 (본문 조회용)
    name: str  # 법령명한글
    law_type: str  # 법령구분명 (법률, 대통령령 등)
    ministry: str  # 소관부처명
    enforcement_date: str  # 시행일자
    status: str  # 현행연혁코드


class LawArticle(BaseModel):
    """법령 조문"""

    article_no: str  # 조문번호
    title: str | None  # 조문제목
    content: str  # 조문내용
    paragraphs: list[dict]  # 항 목록


class LawDetail(BaseModel):
    """법령 상세 정보"""

    mst: str
    name: str
    law_type: str
    ministry: str
    enforcement_date: str
    articles: list[LawArticle]


class LawAPIClient:
    """법령정보 API 클라이언트"""

    def __init__(self):
        self.base_url = settings.LAW_API_BASE_URL
        self.oc = settings.LAW_API_OC

    async def search_laws(
        self,
        query: str | None = None,
        page: int = 1,
        num_of_rows: int = 20,
    ) -> list[LawSummary]:
        """법령 목록 검색

        Args:
            query: 검색 키워드
            page: 페이지 번호
            num_of_rows: 페이지당 결과 수

        Returns:
            법령 요약 목록
        """
        params = {
            "target": "eflaw",
            "OC": self.oc,
            "type": "JSON",
            "page": page,
            "numOfRows": num_of_rows,
        }
        if query:
            params["query"] = query

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/DRF/lawSearch.do",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        laws = data.get("LawSearch", {}).get("law", [])
        if not laws:
            return []

        # 단일 결과인 경우 리스트로 변환
        if isinstance(laws, dict):
            laws = [laws]

        return [
            LawSummary(
                law_id=law.get("법령ID", ""),
                mst=law.get("법령일련번호", ""),
                name=law.get("법령명한글", ""),
                law_type=law.get("법령구분명", ""),
                ministry=law.get("소관부처명", ""),
                enforcement_date=law.get("시행일자", ""),
                status=law.get("현행연혁코드", ""),
            )
            for law in laws
        ]

    async def get_law_detail(self, mst: str) -> LawDetail | None:
        """법령 본문 조회

        Args:
            mst: 법령일련번호

        Returns:
            법령 상세 정보 (조문 포함)
        """
        params = {
            "target": "eflaw",
            "OC": self.oc,
            "type": "JSON",
            "MST": mst,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/DRF/lawService.do",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        law_data = data.get("법령", {})
        if not law_data:
            return None

        # 기본 정보
        basic_info = law_data.get("기본정보", {})

        # 조문 파싱
        articles_data = law_data.get("조문", {}).get("조문단위", [])
        if isinstance(articles_data, dict):
            articles_data = [articles_data]

        articles = []
        for article in articles_data:
            # 항 파싱
            paragraphs = []
            para_data = article.get("항", [])
            if para_data:
                if isinstance(para_data, dict):
                    para_data = [para_data]
                for para in para_data:
                    # 항내용이 리스트인 경우 처리
                    para_content = para.get("항내용", "")
                    if isinstance(para_content, list):
                        para_content = " ".join(
                            str(item) for item in para_content if item
                        )

                    paragraphs.append(
                        {
                            "no": para.get("항번호", ""),
                            "content": para_content,
                            "subparagraphs": para.get("호", []),
                        }
                    )

            # 조문내용이 리스트인 경우 처리
            article_content = article.get("조문내용", "")
            if isinstance(article_content, list):
                article_content = " ".join(
                    str(item) for item in article_content if item
                )

            # 조문제목 처리
            article_title = article.get("조문제목", None)
            if isinstance(article_title, list):
                article_title = " ".join(
                    str(item) for item in article_title if item
                ) or None

            articles.append(
                LawArticle(
                    article_no=article.get("조문번호", ""),
                    title=article_title,
                    content=article_content,
                    paragraphs=paragraphs,
                )
            )

        # 기본 정보 필드 안전하게 추출
        def safe_str(val) -> str:
            if val is None:
                return ""
            if isinstance(val, str):
                return val
            if isinstance(val, dict):
                return val.get("content", str(val))
            if isinstance(val, list):
                return " ".join(str(item) for item in val if item)
            return str(val)

        return LawDetail(
            mst=mst,
            name=safe_str(basic_info.get("법령명_한글", "")),
            law_type=safe_str(basic_info.get("법령구분", "")),
            ministry=safe_str(basic_info.get("소관부처", "")),
            enforcement_date=safe_str(basic_info.get("시행일자", "")),
            articles=articles,
        )

    async def search_law_by_name(self, name: str) -> LawSummary | None:
        """법령명으로 검색하여 현행 법령 반환

        Args:
            name: 법령명 (예: "의료법", "개인정보보호법")

        Returns:
            현행 법령 요약 정보
        """
        laws = await self.search_laws(query=name, num_of_rows=50)

        # 현행이면서 정확히 일치하는 법령 찾기
        for law in laws:
            if law.status == "현행" and law.name == name:
                return law

        # 정확히 일치하는 것이 없으면 현행 중 첫 번째 반환
        for law in laws:
            if law.status == "현행" and name in law.name:
                return law

        return None


# 싱글톤 인스턴스
law_api_client = LawAPIClient()
