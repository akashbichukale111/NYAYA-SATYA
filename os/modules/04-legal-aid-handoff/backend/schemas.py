from typing import Optional, List
from pydantic import BaseModel


class CaseCreate(BaseModel):
    title: str
    citizen_name: Optional[str] = None
    preferred_language: str = "en"


class IntakeSubmit(BaseModel):
    """Maps directly to the guided intake steps in sec 55."""
    what_happened: Optional[str] = None
    who_is_involved: Optional[List[str]] = None
    when_it_happened: Optional[str] = None  # ISO date string, may be omitted
    what_has_happened_since: Optional[str] = None
    deadline_or_hearing: Optional[str] = None
    deadline_date: Optional[str] = None
    requested_help: Optional[str] = None


class HandoffCreate(BaseModel):
    purpose: str
    recipient_role: str
    sender_role: str = "LEGAL_AID_WORKER"


class AcknowledgeRequest(BaseModel):
    action: str  # ACKNOWLEDGE | REQUEST_CLARIFICATION | RETURN_FOR_CORRECTION | ACCEPT
    note: Optional[str] = None


class ClarifyRequest(BaseModel):
    question: str


class ClarifyRespond(BaseModel):
    response: str


class ApprovalRequest(BaseModel):
    approved_by_role: str
    decision: str  # APPROVE | EDIT | REJECT
    note: Optional[str] = None


class SimulateRequest(BaseModel):
    recipient_role: str
    exclude_fact_ids: Optional[List[str]] = None
    exclude_document_ids: Optional[List[str]] = None
    exclude_deadline_ids: Optional[List[str]] = None
