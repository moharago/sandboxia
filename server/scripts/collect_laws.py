"""법령 데이터 수집 및 Vector DB 저장 스크립트 (조/항/호 단위 청킹)

대상 법령:
- 의료법
- 전자금융거래법
- 데이터기본법 (데이터 기본법)
- 신용정보법 (신용정보의 이용 및 보호에 관한 법률)
- 개인정보보호법 (개인정보 보호법)
- 전기통신사업법
- ICT특별법 (정보통신 진흥 및 융합 활성화 등에 관한 특별법)
- 산업융합 촉진법
- 금융혁신지원 특별법
- 지역특구법 (규제자유특구 및 지역특화발전특구에 관한 규제특례법)
- 행정규제기본법

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
import re
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from app.db.export import save_chunks_json
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
    # 규제샌드박스 제도 기본법령
    ("산업융합 촉진법", "regulation"),
    ("금융혁신지원 특별법", "regulation"),
    ("규제자유특구 및 지역특화발전특구에 관한 규제특례법", "regulation"),
    ("행정규제기본법", "regulation"),
]

# 도메인 매핑
DOMAIN_LABELS = {
    "healthcare": "의료/헬스케어",
    "finance": "금융",
    "data": "데이터",
    "privacy": "개인정보",
    "telecom": "통신/ICT",
    "regulation": "규제/제도",
}


def para_symbol_to_index(para_no: str) -> int:
    """항 기호(①②③...)를 숫자 인덱스로 변환

    지원 형식:
    - 원숫자: ①, ②, ③, ...
    - 원숫자+접미사: ①항, ②항, ...
    - 숫자: 1, 2, 3, ...
    - 숫자+접미사: 1항, 2항, 1., 2., ...

    Returns:
        숫자 인덱스 (1부터 시작), 파싱 실패 시 0
    """
    if not para_no:
        return 0

    symbols = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

    # 정규화: 공백 제거, 접미사(항, .) 제거
    normalized = para_no.strip().rstrip("항., ")

    # 1. 원숫자 단일 문자인 경우
    if normalized in symbols:
        return symbols.index(normalized) + 1

    # 2. 첫 글자가 원숫자인 경우 (예: "①항", "②의2")
    if normalized and normalized[0] in symbols:
        return symbols.index(normalized[0]) + 1

    # 3. 숫자로 시작하는 경우 (예: "1", "1항", "12")
    try:
        match = re.match(r"(\d+)", normalized)
        if match:
            return int(match.group(1))
    except ValueError:
        pass

    return 0


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


def create_paragraph_chunks(
    article,
    law_name: str,
    domain: str,
    domain_label: str,
    ministry: str,
    enforcement_date: str,
    mst: str,
) -> tuple[list[Document], list[str]]:
    """조문을 항 단위로 청킹하여 Document 리스트 생성

    Returns:
        (documents, ids): 문서 리스트와 ID 리스트 튜플
    """
    documents = []
    doc_ids = []

    article_no = article.article_no
    article_title = article.title or ""
    article_header = f"제{article_no}조"
    if article_title:
        article_header += f"({article_title})"

    # 항이 있는 경우: 항 단위로 청킹
    if article.paragraphs:
        for enum_idx, para in enumerate(article.paragraphs, start=1):
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
            # ID 생성: law_{mst}_{article_no}_{para_index}
            # 파싱 실패 시 열거 인덱스를 fallback으로 사용
            para_idx = para_symbol_to_index(para_no) or enum_idx
            doc_id = f"law_{mst}_{article_no}_{para_idx}"
            documents.append(doc)
            doc_ids.append(doc_id)

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
            # ID 생성: law_{mst}_{article_no} (항 없음)
            doc_id = f"law_{mst}_{article_no}"
            documents.append(doc)
            doc_ids.append(doc_id)

    return documents, doc_ids


async def collect_and_store_laws(export_chunks: bool = False):
    """법령 데이터 수집 및 Vector DB 저장 (조/항/호 단위 청킹)

    Args:
        export_chunks: True면 청크 JSON도 함께 저장 (평가셋 작성용)
    """

    print("=" * 60)
    print("법령 데이터 수집 시작 (조/항/호 단위 청킹)")
    print("=" * 60)

    # 임베딩 모델 초기화
    embeddings = OpenAIEmbeddings(
        model=settings.LLM_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )

    # Chroma DB 초기화
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma(
        collection_name=COLLECTION_LAWS,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    documents = []
    document_ids = []
    seen_ids: set[str] = set()  # 중복 ID 방지용
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
            article_docs, article_ids = create_paragraph_chunks(
                article=article,
                law_name=law_detail.name,
                domain=domain,
                domain_label=DOMAIN_LABELS.get(domain, domain),
                ministry=law_detail.ministry,
                enforcement_date=law_detail.enforcement_date,
                mst=law_summary.mst,
            )
            documents.extend(article_docs)
            document_ids.extend(article_ids)
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

    # 중복 ID 해결: suffix 추가로 고유성 보장
    unique_ids = []
    duplicate_count = 0
    for doc_id in document_ids:
        if doc_id in seen_ids:
            # 중복 발생 시 suffix 추가
            duplicate_count += 1
            suffix = 1
            new_id = f"{doc_id}_{suffix}"
            while new_id in seen_ids:
                suffix += 1
                new_id = f"{doc_id}_{suffix}"
            doc_id = new_id
        seen_ids.add(doc_id)
        unique_ids.append(doc_id)

    if duplicate_count > 0:
        print(f"\n⚠️  중복 ID {duplicate_count}개 발견 → suffix 추가로 해결")

    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 조문 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # Vector DB에 저장 (고유 ID 포함)
    vectorstore.add_documents(documents, ids=unique_ids)

    print("[OK] Vector DB 저장 완료!")

    # 청크 JSON 저장 (평가용, 플래그가 True일 때만)
    if export_chunks:
        chunks_json_path = Path(__file__).parent.parent / "data" / "r3_data" / "chunks.json"
        saved_count = save_chunks_json(documents, unique_ids, chunks_json_path)
        print(f"[OK] 청크 JSON 저장 완료: {chunks_json_path} ({saved_count}개)")

    # 수집 결과 저장
    result_file = persist_dir / "r3_collection_info.json"
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
        print(
            f"  - {law['name']}: {law['article_count']}개 조문 → {law['chunk_count']}개 청크 ({law['domain']})"
        )
    print(f"\n총 청크 수: {len(documents)}개 (항/조 단위)")
    print(f"저장 위치: {persist_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="법령 데이터 수집 및 Vector DB 저장")
    parser.add_argument(
        "--export-chunks",
        action="store_true",
        help="청크 JSON도 함께 저장 (평가셋 작성용)",
    )
    args = parser.parse_args()

    asyncio.run(collect_and_store_laws(export_chunks=args.export_chunks))
