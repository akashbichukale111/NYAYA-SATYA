from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str
    description: str = ""


class CaseOut(BaseModel):
    id: str
    title: str
    description: str
    is_demo: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClaimCreate(BaseModel):
    text: str
    source: str = "USER_ENTERED"


class ClaimOut(BaseModel):
    id: str
    case_id: str
    text: str
    source: str
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IssueCreate(BaseModel):
    question: str
    description: str = ""


class IssueOut(BaseModel):
    id: str
    case_id: str
    question: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvidenceCreate(BaseModel):
    label: str
    source_text: str = ""
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    extraction_method: str = "MANUAL_ENTRY"


class EvidenceOut(BaseModel):
    id: str
    case_id: str
    document_id: Optional[str]
    label: str
    source_text: str
    page_number: Optional[int]
    section: Optional[str]
    source_location_known: bool
    extraction_method: str
    state: str
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RelationshipCreate(BaseModel):
    source_type: str = Field(..., pattern="^(EVIDENCE|CLAIM|ISSUE)$")
    source_id: str
    target_type: str = Field(..., pattern="^(EVIDENCE|CLAIM|ISSUE)$")
    target_id: str
    relationship_type: str
    support_kind: Optional[str] = None
    explanation: str = ""


class RelationshipOut(BaseModel):
    id: str
    case_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship_type: str
    support_kind: Optional[str]
    verification_status: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CrashTestRequest(BaseModel):
    event_type: str
    target_type: str = Field(..., pattern="^(EVIDENCE|CLAIM|ISSUE)$")
    target_id: str


class ReviewDecision(BaseModel):
    note: str = ""


class IntegrationSummary(BaseModel):
    case_id: str
    evidence_count: int
    claim_count: int
    issue_count: int
    unsupported_claims: int
    unsupported_issues: int
    conflicting_claims: int
    critical_dependencies: List[Dict[str, Any]]
    impact_items: List[Dict[str, Any]]
    verification_pending: int
    provenance_refs: List[str]
    attention_items: List[Dict[str, Any]]
    last_updated: str
