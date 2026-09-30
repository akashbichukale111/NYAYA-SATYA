import uuid
from datetime import datetime

from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum, Integer
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import (
    RoleName, CaseStatus, MembershipRole, AttentionPriority, AttentionType,
    AttentionStatus, SourceEngine, TaskStatus, DateSourceType, NotificationType,
    ReviewKind, ReviewStatus, ApprovalActionType, ApprovalStatus, HandoffStatus,
)


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


# ---------------------------------------------------------------------------
# Identity & access
# ---------------------------------------------------------------------------

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("usr"))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[RoleName] = mapped_column(SAEnum(RoleName), default=RoleName.CITIZEN)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    memberships: Mapped[list["CaseMembership"]] = relationship(back_populates="user")


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("prof"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    organization: Mapped[str | None] = mapped_column(String, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String, nullable=True)
    timezone: Mapped[str] = mapped_column(String, default="Asia/Kolkata")
    dashboard_layout_json: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="profile")


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("ws"))
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("case"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    case_number: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[CaseStatus] = mapped_column(SAEnum(CaseStatus), default=CaseStatus.ACTIVE)
    current_state_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    memberships: Mapped[list["CaseMembership"]] = relationship(back_populates="case")


class CaseMembership(Base, TimestampMixin):
    __tablename__ = "case_memberships"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("mem"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[MembershipRole] = mapped_column(SAEnum(MembershipRole), default=MembershipRole.VIEWER)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    pin_order: Mapped[int] = mapped_column(Integer, default=0)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped["Case"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")


# ---------------------------------------------------------------------------
# Attention
# ---------------------------------------------------------------------------

class CaseAttentionItem(Base, TimestampMixin):
    __tablename__ = "attention_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("att"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    source_entity: Mapped[str] = mapped_column(String)
    type: Mapped[AttentionType] = mapped_column(SAEnum(AttentionType))
    priority: Mapped[AttentionPriority] = mapped_column(SAEnum(AttentionPriority))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[AttentionStatus] = mapped_column(SAEnum(AttentionStatus), default=AttentionStatus.OPEN)
    provenance_refs: Mapped[list] = mapped_column(JSON, default=list)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_safe_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_changed: Mapped[str | None] = mapped_column(Text, nullable=True)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)


# ---------------------------------------------------------------------------
# Tasks & deadlines
# ---------------------------------------------------------------------------

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("task"))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine), default=SourceEngine.SPARK)
    source_entity: Mapped[str | None] = mapped_column(String, nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    priority: Mapped[AttentionPriority] = mapped_column(SAEnum(AttentionPriority), default=AttentionPriority.ATTENTION)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    due_reference_id: Mapped[str | None] = mapped_column(ForeignKey("deadlines.id"), nullable=True)
    requires_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskDependency(Base, TimestampMixin):
    __tablename__ = "task_dependencies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("tdep"))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    depends_on_task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))


class Deadline(Base, TimestampMixin):
    __tablename__ = "deadlines"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("dl"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    label: Mapped[str] = mapped_column(String)
    tracked_date: Mapped[datetime] = mapped_column(DateTime)
    date_source_type: Mapped[DateSourceType] = mapped_column(SAEnum(DateSourceType), default=DateSourceType.UNKNOWN)
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    source_entity: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("notif"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine), default=SourceEngine.SPARK)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), default=NotificationType.IN_APP)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String, index=True)
    read_state: Mapped[bool] = mapped_column(Boolean, default=False)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("npref"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    case_changes: Mapped[bool] = mapped_column(Boolean, default=True)
    deadlines: Mapped[bool] = mapped_column(Boolean, default=True)
    reviews: Mapped[bool] = mapped_column(Boolean, default=True)
    approvals: Mapped[bool] = mapped_column(Boolean, default=True)
    registry_defects: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_conflicts: Mapped[bool] = mapped_column(Boolean, default=True)
    hearing_changes: Mapped[bool] = mapped_column(Boolean, default=True)
    workflow_blockers: Mapped[bool] = mapped_column(Boolean, default=True)
    # Security/audit notifications are intentionally NOT configurable here.


# ---------------------------------------------------------------------------
# Saved views / dashboard
# ---------------------------------------------------------------------------

class SavedView(Base, TimestampMixin):
    __tablename__ = "saved_views"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("view"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    filters_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DashboardLayout(Base, TimestampMixin):
    __tablename__ = "dashboard_layouts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("layout"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    layout_json: Mapped[dict] = mapped_column(JSON, default=dict)


# ---------------------------------------------------------------------------
# Activity / changes / audit / provenance
# ---------------------------------------------------------------------------

class ActivityEvent(Base, TimestampMixin):
    __tablename__ = "activity_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("act"))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String)


class CaseChange(Base, TimestampMixin):
    __tablename__ = "case_changes"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("chg"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    before_json: Mapped[dict] = mapped_column(JSON, default=dict)
    after_json: Mapped[dict] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("rev"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    kind: Mapped[ReviewKind] = mapped_column(SAEnum(ReviewKind))
    what: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    current_state: Mapped[str] = mapped_column(Text)
    proposed_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(SAEnum(ReviewStatus), default=ReviewStatus.PENDING)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("appr"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    action_type: Mapped[ApprovalActionType] = mapped_column(SAEnum(ApprovalActionType))
    description: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String)
    status: Mapped[ApprovalStatus] = mapped_column(SAEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class ActionProposal(Base, TimestampMixin):
    __tablename__ = "action_proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("actp"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    is_consequential: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_request_id: Mapped[str | None] = mapped_column(ForeignKey("approval_requests.id"), nullable=True)


class Handoff(Base, TimestampMixin):
    __tablename__ = "handoffs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("ho"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[HandoffStatus] = mapped_column(SAEnum(HandoffStatus), default=HandoffStatus.PENDING)
    initiated_by: Mapped[str] = mapped_column(String)


class HandoffRecipient(Base, TimestampMixin):
    __tablename__ = "handoff_recipients"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("hor"))
    handoff_id: Mapped[str] = mapped_column(ForeignKey("handoffs.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class SearchIndexRecord(Base, TimestampMixin):
    __tablename__ = "search_index_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("srch"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[str] = mapped_column(Text)


class EngineConnection(Base, TimestampMixin):
    __tablename__ = "engine_connections"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("econn"))
    engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    status: Mapped[str] = mapped_column(String, default="demo_stub")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EngineEvent(Base, TimestampMixin):
    __tablename__ = "engine_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("eev"))
    engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)


class IntegrationSnapshot(Base, TimestampMixin):
    __tablename__ = "integration_snapshots"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("isnap"))
    engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("aud"))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String)
    target_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)


class ProvenanceRecord(Base, TimestampMixin):
    __tablename__ = "provenance_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("prov"))
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    source_engine: Mapped[SourceEngine] = mapped_column(SAEnum(SourceEngine))
    source_reference: Mapped[str] = mapped_column(String)
    confidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class SimulationReference(Base, TimestampMixin):
    __tablename__ = "simulation_references"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: gen_id("sim"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    label: Mapped[str] = mapped_column(String)
    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)
