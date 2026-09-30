from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProvenanceState, DeadlineStatus, SourceType


class IngestTextRequest(BaseModel):
    label: str = Field(..., description="Human-readable name, e.g. filename or 'manual note'")
    text: str = Field(..., min_length=1)
    source_type: SourceType = SourceType.MANUAL_ENTRY


class DateCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    raw_span: str
    context_snippet: str
    resolved_date: Optional[datetime]
    is_relative: bool
    relative_anchor_hint: Optional[str]
    provenance_state: ProvenanceState
    confidence: float


class DeadlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    status: DeadlineStatus
    provenance_state: ProvenanceState
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    source_type: SourceType
    ingested_at: datetime
    date_candidates: List[DateCandidateOut] = []


class ReviewDeadlineRequest(BaseModel):
    reviewer: str = Field(..., min_length=1, description="Human identifier performing the review")
    approve: bool
    corrected_due_date: Optional[datetime] = Field(
        None, description="If the human is correcting the date rather than just confirming it"
    )
    note: Optional[str] = None
