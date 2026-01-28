"""Document Parsers

HWP, PDF 등 문서 파싱 서비스

지원하는 HWP 문서 유형:
1. 상담신청 (counseling): 1개
2. 신속확인 (fastcheck): 2개
3. 임시허가 (temporary): 4개
4. 실증특례 (demonstration): 4개

파일 구조:
- hwp_parser.py: HWP 파싱 로직 (HWPParser, HWPDocument 등)
- hwp_patterns.py: 문서 유형별 필드 추출 패턴
"""

from app.services.parsers.hwp_parser import (
    HWPDocument,
    HWPParser,
    HWPSection,
    merge_parsed_documents,
    parse_hwp_file,
    parse_hwp_files,
)
from app.services.parsers.hwp_patterns import (
    DocumentCategory,
    DocumentSubtype,
    get_patterns_for_subtype,
)

__all__ = [
    # Classes
    "HWPParser",
    "HWPDocument",
    "HWPSection",
    # Enums
    "DocumentCategory",
    "DocumentSubtype",
    # Parser Functions
    "parse_hwp_file",
    "parse_hwp_files",
    "merge_parsed_documents",
    # Pattern Functions
    "get_patterns_for_subtype",
]
