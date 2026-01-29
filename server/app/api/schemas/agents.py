"""Agent API 스키마"""

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    """파싱된 문서"""

    file_index: int
    original_filename: str
    assigned_subtype: str | None = None
    detected_type: str | None = None
    detected_subtype: str | None = None
    parse_success: bool = True
    error_message: str | None = None


class StructureResponse(BaseModel):
    """서비스 구조화 응답"""

    session_id: str
    requested_track: str
    canonical_structure: dict | None = None
    parsed_documents: list[ParsedDocument] = Field(default_factory=list)
    error: str | None = None
    messages: list[dict] = Field(default_factory=list)
