"""RAG tools module"""

# R1. 규제제도 & 절차 RAG
from app.tools.shared.rag.regulation_rag import (
    search_regulation,
    get_track_definition,
    get_application_requirements,
    get_review_criteria,
    compare_tracks,
    list_available_tracks,
)

# R2. 승인 사례 RAG
from app.tools.shared.rag.case_rag import (
    search_case,
    get_similar_cases_for_application,
    get_case_detail,
    get_approval_patterns,
    list_available_tracks as list_case_tracks,
)

# R3. 도메인별 규제·법령 RAG
from app.tools.shared.rag.domain_law_rag import (
    search_domain_law,
)

__all__ = [
    # R1. 규제제도 & 절차
    "search_regulation",
    "get_track_definition",
    "get_application_requirements",
    "get_review_criteria",
    "compare_tracks",
    "list_available_tracks",
    # R2. 승인 사례
    "search_case",
    "get_similar_cases_for_application",
    "get_case_detail",
    "get_approval_patterns",
    "list_case_tracks",
    # R3. 도메인별 법령
    "search_domain_law",
]
