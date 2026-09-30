from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class CaseCreate(BaseModel):
    case_reference: str
    title: str
    jurisdiction_note: Optional[str] = None
    person_full_name: str


class CaseOut(BaseModel):
    id: str
    case_reference: str
    title: str
    jurisdiction_note: Optional[str]
    is_demo: bool
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: str
    case_id: str
    filename: str
    document_type: str
    mime_type: str
    status: str
    extraction_method: Optional[str]
    sha256: str
    rejection_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ManualCustodyEventCreate(BaseModel):
    event_type: str
    event_date: Optional[str] = None
    date_type: str = "USER_ENTERED_DATE"
    notes: Optional[str] = None


class ReviewDecision(BaseModel):
    note: Optional[str] = None


class SimulationRequest(BaseModel):
    event_type: str
    target_entity_id: Optional[str] = None


class CrashTestRequest(BaseModel):
    event_type: str
    target_entity_id: Optional[str] = None


class IntegrationAdapterOut(BaseModel):
    case_id: str
    custody_state: str
    custody_state_confidence: str
    latest_verified_event: Optional[Any]
    upcoming_tracked_events: List[Any]
    attention_items: List[Any]
    conflicts: List[Any]
    missing_information: List[str]
    verification_pending: List[Any]
    dependency_items: List[Any]
    provenance_refs: List[Any]
    last_updated: Optional[str]
