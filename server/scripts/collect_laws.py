"""법령 데이터 수집 및 Vector DB 저장 스크립트 (조/항/호 단위 청킹)

대상 법령:
- 의료법
- 전자금융거래법
- 데이터기본법 (데이터 기본법)
- 신용정보법 (신용정보의 이용 및 보호에 관한 법률)
- 개인정보보호법 (개인정보 보호법)
- 전기통신사업법
- ICT특별법 (정보통신 진흥 및 융합 활성화 등에 관한 특별법)

청킹 전략:
- 항(①②③) 단위로 청킹 (하위 호/목 포함)
- 항이 없는 조문은 조 단위로 청킹
- 상위 조문 정보를 메타데이터에 포함하여 컨텍스트 유지

실행:
    cd server
    uv run python scripts/collect_laws.py
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.services.law_api import law_api_client

# 수집 대상 법령 (검색명, 도메인)
TARGET_LAWS = [
    ("의료법", "healthcare"),
    ("전자금융거래법", "finance"),
    ("데이터 산업진흥 및 이용촉진에 관한 기본법", "data"),
    ("신용정보의 이용 및 보호에 관한 법률", "finance"),
    ("개인정보 보호법", "privacy"),
    ("전기통신사업법", "telecom"),
    ("정보통신 진흥 및 융합 활성화 등에 관한 특별법", "telecom"),
]

# 도메인 매핑
DOMAIN_LABELS = {
    "healthcare": "의료/헬스케어",
    "finance": "금융",
    "data": "데이터",
    "privacy": "개인정보",
    "telecom": "통신/ICT",
}


def format_subparagraphs(subparas: list) -> str:
    """호/목 내용을 텍스트로 포맷팅"""
    lines = []
    if not subparas:
        return ""

    if isinstance(subparas, dict):
        subparas = [subparas]

    for subpara in subparas:
        if isinstance(subpara, dict):
            sub_no = subpara.get("호번호", "")
            sub_content = subpara.get("호내용", "")
            if sub_content:
                lines.append(f"  {sub_no}. {sub_content}")

            # 목 처리
            items = subpara.get("목", [])
            if items:
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    if isinstance(item, dict):
                        item_no = item.get("목번호", "")
                        item_content = item.get("목내용", "")
                        if item_content:
                            lines.append(f"    {item_no}. {item_content}")

    return "\n".join(lines)


def create_paragraph_chunks(article, law_name: str, domain: str, domain_label: str,
                            ministry: str, enforcement_date: str, mst: str) -> list[Document]:
    """조문을 항 단위로 청킹하여 Document 리스트 생성"""
    documents = []

    article_no = article.article_no
    article_title = article.title or ""
    article_header = f"제{article_no}조"
    if article_title:
        article_header += f"({article_title})"

    # 항이 있는 경우: 항 단위로 청킹
    if article.paragraphs:
        for para in article.paragraphs:
            para_no = para.get("no", "")
            para_content = para.get("content", "")

            if not para_content:
                continue

            # 항 내용 + 하위 호/목
            content_lines = [
                f"[{law_name}] {article_header}",
                f"{para_no} {para_content}",
            ]

            # 호/목 추가
            subparas_text = format_subparagraphs(para.get("subparagraphs", []))
            if subparas_text:
                content_lines.append(subparas_text)

            content = "\n".join(content_lines)

            # 인용 형식 생성 (예: 의료법 제34조 제1항)
            citation = f"{law_name} 제{article_no}조"
            if para_no:
                citation += f" {para_no}"

            doc = Document(
                page_content=content,
                metadata={
                    "source_type": "law",
                    "law_name": law_name,
                    "law_mst": mst,
                    "article_no": article_no,
                    "article_title": article_title,
                    "paragraph_no": para_no,
                    "chunk_type": "paragraph",  # 항 단위
                    "citation": citation,
                    "domain": domain,
                    "domain_label": domain_label,
                    "ministry": ministry,
                    "enforcement_date": enforcement_date,
                },
            )
            documents.append(doc)

    # 항이 없는 경우: 조 단위로 청킹
    else:
        content_lines = [
            f"[{law_name}] {article_header}",
        ]
        if article.content:
            content_lines.append(article.content)

        content = "\n".join(content_lines)

        if content.strip():
            citation = f"{law_name} 제{article_no}조"

            doc = Document(
                page_content=content,
                metadata={
                    "source_type": "law",
                    "law_name": law_name,
                    "law_mst": mst,
                    "article_no": article_no,
                    "article_title": article_title,
                    "paragraph_no": "",
                    "chunk_type": "article",  # 조 단위
                    "citation": citation,
                    "domain": domain,
                    "domain_label": domain_label,
                    "ministry": ministry,
                    "enforcement_date": enforcement_date,
                },
            )
            documents.append(doc)

    return documents


async def collect_and_store_laws():
    """법령 데이터 수집 및 Vector DB 저장 (조/항/호 단위 청킹)"""

    print("=" * 60)
    print("법령 데이터 수집 시작 (조/항/호 단위 청킹)")
    print("=" * 60)

    # 임베딩 모델 초기화
    embeddings = OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Chroma DB 초기화
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma(
        collection_name="domain_laws",
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    documents = []
    collected_laws = []

    for law_name, domain in TARGET_LAWS:
        print(f"\n[{law_name}] 검색 중...")

        # 법령 검색
        law_summary = await law_api_client.search_law_by_name(law_name)
        if not law_summary:
            print(f"  ⚠️  '{law_name}' 법령을 찾을 수 없습니다.")
            continue

        print(f"  [OK] 발견: {law_summary.name} (MST: {law_summary.mst})")
        print(f"    - 소관부처: {law_summary.ministry}")
        print(f"    - 시행일자: {law_summary.enforcement_date}")

        # 본문 조회
        law_detail = await law_api_client.get_law_detail(law_summary.mst)
        if not law_detail:
            print("  ⚠️  본문 조회 실패")
            continue

        print(f"  [OK] 조문 수: {len(law_detail.articles)}개")

        # 조문별로 항 단위 청킹
        law_doc_count = 0
        for article in law_detail.articles:
            article_docs = create_paragraph_chunks(
                article=article,
                law_name=law_detail.name,
                domain=domain,
                domain_label=DOMAIN_LABELS.get(domain, domain),
                ministry=law_detail.ministry,
                enforcement_date=law_detail.enforcement_date,
                mst=law_summary.mst,
            )
            documents.extend(article_docs)
            law_doc_count += len(article_docs)

        print(f"  [OK] 생성된 청크: {law_doc_count}개 (항/조 단위)")

        collected_laws.append(
            {
                "name": law_detail.name,
                "mst": law_summary.mst,
                "domain": domain,
                "article_count": len(law_detail.articles),
                "chunk_count": law_doc_count,
            }
        )

    if not documents:
        print("\n⚠️  수집된 문서가 없습니다.")
        return

    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 조문 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # Vector DB에 저장
    vectorstore.add_documents(documents)

    print("[OK] 저장 완료!")

    # 수집 결과 저장
    result_file = persist_dir / "collection_info.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_documents": len(documents),
                "laws": collected_laws,
                "domains": list(DOMAIN_LABELS.keys()),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n수집 정보 저장: {result_file}")
    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    for law in collected_laws:
        print(f"  - {law['name']}: {law['article_count']}개 조문 → {law['chunk_count']}개 청크 ({law['domain']})")
    print(f"\n총 청크 수: {len(documents)}개 (항/조 단위)")
    print(f"저장 위치: {persist_dir}")


if __name__ == "__main__":
    asyncio.run(collect_and_store_laws())
