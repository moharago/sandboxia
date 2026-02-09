"""청크 데이터 내보내기 유틸리티

Vector DB 저장 시 청크 JSON도 함께 저장하기 위한 공통 함수.
"""

import json
from pathlib import Path

from langchain_core.documents import Document


def save_chunks_json(
    documents: list[Document],
    doc_ids: list[str],
    output_path: Path,
) -> int:
    """Document 리스트를 청크 JSON으로 저장

    Args:
        documents: LangChain Document 리스트
        doc_ids: 문서 ID 리스트
        output_path: 저장할 JSON 파일 경로

    Returns:
        저장된 청크 수
    """
    chunks = []
    for doc, chunk_id in zip(documents, doc_ids, strict=True):
        chunks.append(
            {
                "chunk_id": chunk_id,
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
        )

    # 도메인/카테고리별로 정렬 (있으면)
    def sort_key(c):
        m = c["metadata"]
        return (
            m.get("domain", m.get("category", "")),
            c["chunk_id"],
        )

    chunks.sort(key=sort_key)

    # 디렉토리 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # JSON 저장
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_count": len(chunks),
                "chunks": chunks,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return len(chunks)
