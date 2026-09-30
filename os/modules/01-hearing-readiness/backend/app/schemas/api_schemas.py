from __future__ import annotations

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str
    case_type: str
    parties: list[dict] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    decision: str  # APPROVE / EDIT / REJECT
    approved_by: str = "demo_user"
    edited_description: str | None = None
    notes: str | None = None


class SimulateRequest(BaseModel):
    hypothesis: list[dict]


class CrashTestRequest(BaseModel):
    mutation: str | None = None  # None => run all mutations


class VersionDiffRequest(BaseModel):
    from_version: int
    to_version: int
