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


# ============================================================
# Canonical Structure 모델
# ============================================================


class CompanyInfo(BaseModel):
    """회사 정보"""

    company_name: str | None = None
    representative: str | None = None
    business_number: str | None = None
    address: str | None = None
    contact: str | None = None
    email: str | None = None


class ServiceInfo(BaseModel):
    """서비스 정보"""

    service_name: str | None = None
    what_action: str | None = None
    target_users: str | None = None
    delivery_method: str | None = None
    service_description: str | None = None
    service_category: str | None = None


class TechnologyInfo(BaseModel):
    """기술 정보"""

    core_technology: str | None = None
    innovation_points: list[str] = Field(default_factory=list)


class RegulatoryIssue(BaseModel):
    """규제 이슈 항목"""

    summary: str | None = None
    problematic_action: str | None = None
    status: str | None = None  # unclear | blocked | license_required | requirement_mismatch | no_basis | allowed_but_conditions
    blocking_reason: str | None = None
    relief_direction: str | None = None  # interpretation_needed | temporary_permission | pilot_exception


class RegulatoryInfo(BaseModel):
    """규제 정보"""

    related_regulations: list[str] = Field(default_factory=list)
    regulatory_issues: list[RegulatoryIssue] = Field(default_factory=list)


class FieldConfidence(BaseModel):
    """필드별 신뢰도"""

    company: float = 0.0
    service: float = 0.0
    technology: float = 0.0
    regulatory: float = 0.0


class CanonicalMetadata(BaseModel):
    """Canonical Structure 메타데이터"""

    source_type: str | None = None
    session_id: str | None = None
    created_at: str | None = None
    field_confidence: FieldConfidence = Field(default_factory=FieldConfidence)
    missing_fields: list[str] = Field(default_factory=list)
    consultant_memo: str | None = None


class CanonicalStructure(BaseModel):
    """Canonical Structure - 서비스 구조화 결과"""

    company: CompanyInfo = Field(default_factory=CompanyInfo)
    service: ServiceInfo = Field(default_factory=ServiceInfo)
    technology: TechnologyInfo = Field(default_factory=TechnologyInfo)
    regulatory: RegulatoryInfo = Field(default_factory=RegulatoryInfo)
    metadata: CanonicalMetadata = Field(default_factory=CanonicalMetadata)


# ============================================================
# API Response 모델
# ============================================================


class StructureResponse(BaseModel):
    """서비스 구조화 응답"""

    session_id: str
    requested_track: str
    canonical_structure: CanonicalStructure | None = None
    parsed_documents: list[ParsedDocument] = Field(default_factory=list)
    error: str | None = None
    messages: list[dict] = Field(default_factory=list)
