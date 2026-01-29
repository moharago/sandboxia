"""Service Structurer Agent Tools

HWP Parser Tool - HWP 파일 파싱
"""

from typing import Any

from langchain_core.tools import tool

from app.services.parsers.hwp_parser import (
    HWPDocument,
    merge_parsed_documents,
    parse_hwp_files,
)
from app.services.parsers.hwp_patterns import DocumentCategory, DocumentSubtype


def _hwp_document_to_dict(doc: HWPDocument) -> dict[str, Any]:
    """HWPDocument를 딕셔너리로 변환"""
    return {
        "file_name": doc.file_name,
        "document_type": doc.document_category.value,
        "document_subtype": doc.document_subtype.value,
        "raw_text": doc.raw_text,
        "sections": [
            {
                "index": s.index,
                "title": s.title,
                "content": s.content,
            }
            for s in doc.sections
        ],
        "extracted_fields": doc.extracted_fields,
        "parse_success": doc.parse_success,
        "error_message": doc.error_message if doc.error_message else None,
    }


@tool
def parse_hwp_documents(
    file_paths: list[str],
    document_subtypes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """HWP 문서를 파싱

    HWP 파일을 파싱하여 구조화된 데이터 리스트로 반환합니다.

    Args:
        file_paths: HWP 파일 경로 리스트
        document_subtypes: 각 파일의 서브타입 리스트 (optional)

    Returns:
        파싱된 문서 정보 리스트
    """
    docs = parse_hwp_files(file_paths, document_subtypes)
    return [_hwp_document_to_dict(doc) for doc in docs]


@tool
def merge_hwp_documents(
    parse_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """여러 파싱 결과를 하나로 병합

    같은 카테고리의 여러 문서(예: temporary-1~4)에서 추출한 필드들을
    하나의 구조로 병합합니다.

    Args:
        parse_results: HWP 파싱 결과 리스트

    Returns:
        병합된 필드 딕셔너리 (company_info, service_info, technology_info 등)
    """
    # dict를 HWPDocument로 변환
    documents = []
    for result in parse_results:
        doc = HWPDocument(
            file_path="",
            file_name=result.get("file_name", ""),
            raw_text=result.get("raw_text", ""),
            extracted_fields=result.get("extracted_fields", {}),
            parse_success=result.get("parse_success", False),
            error_message=result.get("error_message", ""),
        )
        # 카테고리와 서브타입 설정
        try:
            doc.document_subtype = DocumentSubtype(
                result.get("document_subtype", "unknown")
            )
            subtype_value = doc.document_subtype.value
            if subtype_value.startswith("counseling"):
                doc.document_category = DocumentCategory.COUNSELING
            elif subtype_value.startswith("fastcheck"):
                doc.document_category = DocumentCategory.FASTCHECK
            elif subtype_value.startswith("temporary"):
                doc.document_category = DocumentCategory.TEMPORARY
            elif subtype_value.startswith("demonstration"):
                doc.document_category = DocumentCategory.DEMONSTRATION
        except ValueError:
            pass

        documents.append(doc)

    return merge_parsed_documents(documents)
