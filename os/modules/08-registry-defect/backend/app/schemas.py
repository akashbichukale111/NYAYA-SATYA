"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, Any


class CaseCreate(BaseModel):
    title: str
    case_reference: Optional[str] = None


class CaseOut(BaseModel):
    id: str
    title: str
    case_reference: Optional[str] = None
    status: str
    is_demo: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class FilingPackageCreate(BaseModel):
    name: str


class FilingPackageOut(BaseModel):
    id: str
    case_id: str
    name: str
    lifecycle_state: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RequirementCreate(BaseModel):
    requirement_type: str
    description: str
    source: str
    source_reference: Optional[str] = None
    target_reference_label: Optional[str] = None
    jurisdiction: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None


class RequirementOut(BaseModel):
    id: str
    case_id: str
    filing_package_id: str
    requirement_type: str
    description: str
    source: str
    source_reference: Optional[str]
    version: int
    status: str
    verification_status: str
    target_reference_label: Optional[str]
    jurisdiction: Optional[str]
    effective_from: Optional[str]
    effective_until: Optional[str]

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    case_id: str
    filing_package_id: str
    display_name: str
    document_kind: Optional[str]
    status: str
    current_version_id: Optional[str]

    class Config:
        from_attributes = True


class DocumentVersionOut(BaseModel):
    id: str
    document_id: str
    version_number: int
    original_filename: str
    mime_type: Optional[str]
    detected_format: Optional[str]
    size_bytes: int
    sha256: Optional[str]
    extraction_status: str
    extraction_error: Optional[str]
    page_count: Optional[int]
    quarantined: bool
    quarantine_reason: Optional[str]
    source_location_known: bool

    class Config:
        from_attributes = True


class ChecklistItemOut(BaseModel):
    id: str
    requirement_id: str
    status: str
    source: Optional[str]
    document_refs: list
    evidence_refs: list
    verification: str
    review_state: str
    explanation: Optional[str]

    class Config:
        from_attributes = True


class DefectOut(BaseModel):
    id: str
    case_id: str
    filing_package_id: str
    defect_type: str
    category: str
    severity: str
    status: str
    description: str
    source_refs: list
    document_refs: list
    requirement_refs: list
    detected_by: str
    detected_at: str
    verification_status: str
    human_review_required: bool
    resolution_note: Optional[str]

    class Config:
        from_attributes = True


class ObjectionCreate(BaseModel):
    original_text: str
    source_reference: Optional[str] = None


class ObjectionOut(BaseModel):
    id: str
    case_id: str
    filing_package_id: str
    original_text: str
    source_reference: Optional[str]
    status: str
    linked_defect_id: Optional[str]

    class Config:
        from_attributes = True


class CorrectionCreate(BaseModel):
    defect_id: Optional[str] = None
    objection_id: Optional[str] = None
    description: str
    suggested_action: Optional[str] = None


class CorrectionOut(BaseModel):
    id: str
    case_id: str
    filing_package_id: str
    defect_id: Optional[str]
    objection_id: Optional[str]
    description: str
    suggested_action: Optional[str]
    status: str

    class Config:
        from_attributes = True


class ReviewDecisionIn(BaseModel):
    reason: Optional[str] = None


class ReviewTaskOut(BaseModel):
    id: str
    case_id: str
    target_type: str
    target_id: str
    action_requested: str
    decision: str
    reason: Optional[str]

    class Config:
        from_attributes = True


class SimulationRequest(BaseModel):
    scenario: str
    params: dict = Field(default_factory=dict)


class AuditEventOut(BaseModel):
    id: str
    actor_user_id: Optional[str]
    actor_role: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    reason: Optional[str]
    timestamp: str

    class Config:
        from_attributes = True


class NyayaSatyaSummary(BaseModel):
    case_id: str
    filing_packages: int
    open_defects: int
    high_attention_defects: int
    missing_documents: list
    missing_references: list
    metadata_conflicts: list
    duplicate_groups: list
    open_objections: list
    corrections_pending: list
    verification_pending: list
    blocked_workflows: list
    attention_items: list
    provenance_refs: list
    last_updated: str
