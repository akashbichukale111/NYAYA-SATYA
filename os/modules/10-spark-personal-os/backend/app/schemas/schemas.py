import re
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, AfterValidator

from app.models.enums import (
    RoleName, CaseStatus, AttentionPriority, AttentionType, AttentionStatus,
    SourceEngine, TaskStatus, DateSourceType, ReviewKind, ReviewStatus,
    ApprovalActionType, ApprovalStatus,
)


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---

# Deliberately not using pydantic's EmailStr here: its underlying email-validator
# library rejects RFC 2606 reserved test domains (.test, .example, .invalid),
# which this project's own DEMO seed data uses on purpose. We still validate a
# sane email *shape* server-side; deliverability is out of scope for an
# internal case-management login.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _check_email_shape(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("value is not a valid email address")
    return value.lower()


EmailLike = Annotated[str, AfterValidator(_check_email_shape)]


class UserRegister(BaseModel):
    email: EmailLike
    password: str
    full_name: str
    role: RoleName = RoleName.CITIZEN


class UserLogin(BaseModel):
    email: EmailLike
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMBase):
    id: str
    email: str
    full_name: str
    role: RoleName
    is_active: bool


# --- Cases ---

class CaseOut(ORMBase):
    id: str
    case_number: str
    title: str
    status: CaseStatus
    current_state_summary: str | None
    is_demo: bool
    updated_at: datetime


class CaseCreate(BaseModel):
    case_number: str
    title: str
    current_state_summary: str | None = None


# --- Attention ---

class AttentionItemOut(ORMBase):
    id: str
    case_id: str
    source_engine: SourceEngine
    source_entity: str
    type: AttentionType
    priority: AttentionPriority
    reason: str
    status: AttentionStatus
    provenance_refs: list
    requires_human_review: bool
    recommended_safe_action: str | None
    what_changed: str | None
    dependencies: list
    created_at: datetime
    updated_at: datetime


# --- Tasks ---

class TaskOut(ORMBase):
    id: str
    case_id: str | None
    title: str
    description: str | None
    source_engine: SourceEngine
    source_entity: str | None
    assignee_id: str | None
    priority: AttentionPriority
    status: TaskStatus
    requires_verification: bool
    verification_confirmed_by: str | None
    completed_at: datetime | None
    created_at: datetime


class TaskCreate(BaseModel):
    case_id: str | None = None
    title: str
    description: str | None = None
    priority: AttentionPriority = AttentionPriority.ATTENTION
    assignee_id: str | None = None
    requires_verification: bool = False


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    verification_confirmed: bool = False


# --- Deadlines ---

class DeadlineOut(ORMBase):
    id: str
    case_id: str
    label: str
    tracked_date: datetime
    date_source_type: DateSourceType
    source_engine: SourceEngine
    source_entity: str | None
    notes: str | None


# --- Reviews ---

class ReviewTaskOut(ORMBase):
    id: str
    case_id: str
    kind: ReviewKind
    what: str
    why: str
    source_engine: SourceEngine
    evidence_refs: list
    current_state: str
    proposed_action: str | None
    status: ReviewStatus
    decided_by: str | None
    decided_at: datetime | None
    decision_note: str | None


class ReviewDecision(BaseModel):
    status: ReviewStatus
    decision_note: str | None = None


# --- Approvals ---

class ApprovalRequestOut(ORMBase):
    id: str
    case_id: str
    action_type: ApprovalActionType
    description: str
    requested_by: str
    status: ApprovalStatus
    decided_by: str | None
    decided_at: datetime | None


class ApprovalDecision(BaseModel):
    status: ApprovalStatus


# --- Changes ---

class CaseChangeOut(ORMBase):
    id: str
    case_id: str
    source_engine: SourceEngine
    entity_type: str
    entity_id: str
    before_json: dict
    after_json: dict
    actor: str
    occurred_at: datetime


# --- Notifications ---

class NotificationOut(ORMBase):
    id: str
    case_id: str | None
    source_engine: SourceEngine
    type: str
    title: str
    body: str
    read_state: bool
    created_at: datetime


# --- Saved views ---

class SavedViewCreate(BaseModel):
    name: str
    filters_json: dict


class SavedViewOut(ORMBase):
    id: str
    name: str
    filters_json: dict


# --- Case digest ---

class CaseDigestOut(BaseModel):
    case_id: str
    current_state: str
    what_changed: list[str]
    needs_attention: list[str]
    blocked: list[str]
    unknown: list[str]
    needs_review: list[str]
    next_safe_actions: list[str]
    generated_at: datetime


# --- Workspace summary ---

class WorkspaceSummaryOut(BaseModel):
    my_cases_count: int
    my_attention_count: int
    my_tasks_open_count: int
    my_deadlines_upcoming_count: int
    my_reviews_pending_count: int
    my_approvals_pending_count: int
    my_handoffs_pending_count: int
