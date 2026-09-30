"""
Domain models for the Case Continuity Engine.

Design notes:
- Case history is EVENT-SOURCED: `Event` rows are append-only and are never
  deleted or mutated by normal application code (see app/agents/orchestrator.py).
- The "current" mutable-looking entities (Deadline, Obligation, etc.) always
  carry a `status` and `superseded_by_event_id` rather than being deleted,
  so old values remain inspectable (see section 12, Stale State Detection).
- `StateVersion` is an immutable snapshot pointer: each version stores a
  JSON snapshot of the twin at that point plus the event that produced it.
- No field here is a "giant JSON blob" replacement for the relational model;
  JSON snapshot columns exist ONLY on StateVersion, purely as a cached
  materialization for fast diffing/time-travel, never as the source of truth.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _id() -> str:
    return uuid.uuid4().hex[:16]


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventType(str, enum.Enum):
    DOCUMENT_UPLOADED = "document_uploaded"
    ORDER_RECEIVED = "order_received"
    HEARING_OCCURRED = "hearing_occurred"
    FILING_ADDED = "filing_added"
    REPLY_RECEIVED = "reply_received"
    NOTICE_ISSUED = "notice_issued"
    SERVICE_RECORDED = "service_recorded"
    DEADLINE_CREATED = "deadline_created"
    DEADLINE_MODIFIED = "deadline_modified"
    DEADLINE_COMPLETED = "deadline_completed"
    OBLIGATION_CREATED = "obligation_created"
    OBLIGATION_SATISFIED = "obligation_satisfied"
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_STATUS_CHANGED = "evidence_status_changed"
    HUMAN_ACTION = "human_action"
    AGENT_ACTION = "agent_action"
    VERIFICATION_EVENT = "verification_event"
    CASE_CREATED = "case_created"


class ChangeNature(str, enum.Enum):
    NEW = "new"
    DUPLICATE = "duplicate"
    CONTRADICTION = "contradiction"
    UPDATE = "update"
    CORRECTION = "correction"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"
    UNRELATED = "unrelated"


class ReviewStatus(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class ItemStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    BLOCKED = "blocked"


class ConflictType(str, enum.Enum):
    DATE_CONFLICT = "date_conflict"
    STATUS_CONFLICT = "status_conflict"
    PARTY_CONFLICT = "party_conflict"
    DOCUMENT_VERSION_CONFLICT = "document_version_conflict"
    DEADLINE_CONFLICT = "deadline_conflict"
    EVENT_ORDER_CONFLICT = "event_order_conflict"
    SOURCE_CONFLICT = "source_conflict"


class VerificationResult(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


# ---------------------------------------------------------------------------
# Core case + parties
# ---------------------------------------------------------------------------

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    title: Mapped[str] = mapped_column(String)
    case_number: Mapped[str] = mapped_column(String, default="")
    court: Mapped[str] = mapped_column(String, default="")
    procedural_stage: Mapped[str] = mapped_column(String, default="Intake")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    demo_case_key: Mapped[str] = mapped_column(String, default="")  # e.g. "CASE_A"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    current_version_number: Mapped[int] = mapped_column(Integer, default=0)

    parties: Mapped[list["Party"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Party(Base):
    __tablename__ = "parties"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="")  # petitioner/respondent/legal_aid/advocate...
    representative: Mapped[str] = mapped_column(String, default="")

    case: Mapped["Case"] = relationship(back_populates="parties")


# ---------------------------------------------------------------------------
# Event-sourced history (append-only)
# ---------------------------------------------------------------------------

class Event(Base):
    """
    Append-only case history. Never updated or deleted by app logic.
    """
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    event_type: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)
    source: Mapped[str] = mapped_column(String, default="")           # e.g. document id, "manual", "system"
    actor: Mapped[str] = mapped_column(String, default="system")      # human name/id or agent name
    description: Mapped[str] = mapped_column(Text, default="")
    structured_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)      # {document_id, page, section, agent_run_id}
    correlation_id: Mapped[str] = mapped_column(String, default="")

    case: Mapped["Case"] = relationship(back_populates="events")


# ---------------------------------------------------------------------------
# Documents & Evidence
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    filename: Mapped[str] = mapped_column(String)
    doc_type: Mapped[str] = mapped_column(String, default="unclassified")  # order/filing/notice/reply/evidence...
    stored_path: Mapped[str] = mapped_column(String, default="")
    sha256: Mapped[str] = mapped_column(String, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    extracted_text_preview: Mapped[str] = mapped_column(Text, default="")
    prompt_injection_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False)

    case: Mapped["Case"] = relationship(back_populates="documents")


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=True)
    label: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default=ItemStatus.OPEN.value)  # open/verified/superseded/unavailable
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    source_event_id: Mapped[str] = mapped_column(String, default="")


# ---------------------------------------------------------------------------
# Hearings, Orders, Deadlines, Obligations, Actions
# ---------------------------------------------------------------------------

class Hearing(Base):
    __tablename__ = "hearings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    scheduled_date: Mapped[str] = mapped_column(String, default="")  # ISO date string
    occurred: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome_summary: Mapped[str] = mapped_column(Text, default="")
    source_event_id: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default=ItemStatus.OPEN.value)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id"), nullable=True)
    order_date: Mapped[str] = mapped_column(String, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default=ItemStatus.OPEN.value)
    source_event_id: Mapped[str] = mapped_column(String, default="")


class Deadline(Base):
    __tablename__ = "deadlines"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    label: Mapped[str] = mapped_column(String)
    due_date: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default=ItemStatus.OPEN.value)
    reason: Mapped[str] = mapped_column(Text, default="")
    source_event_id: Mapped[str] = mapped_column(String, default="")
    superseded_by_event_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Obligation(Base):
    __tablename__ = "obligations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    description: Mapped[str] = mapped_column(Text)
    owner_party: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default=ItemStatus.OPEN.value)  # open/resolved/superseded/blocked
    due_date: Mapped[str] = mapped_column(String, default="")
    source_event_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Action(Base):
    __tablename__ = "actions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    description: Mapped[str] = mapped_column(Text)
    assignee: Mapped[str] = mapped_column(String, default="unassigned")
    status: Mapped[str] = mapped_column(String, default=ItemStatus.OPEN.value)
    source_event_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# State versioning + diff + conflicts
# ---------------------------------------------------------------------------

class StateVersion(Base):
    __tablename__ = "state_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    triggering_event_id: Mapped[str] = mapped_column(String, default="")
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)  # materialized twin snapshot, cache only
    freshness: Mapped[str] = mapped_column(String, default="UNKNOWN")


class StateChange(Base):
    """A single diffed field/entity change between two StateVersions."""
    __tablename__ = "state_changes"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    from_version: Mapped[int] = mapped_column(Integer)
    to_version: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String)  # ADDED/REMOVED/CHANGED/RESOLVED/NEWLY_BLOCKED/STALE/UNCERTAIN
    entity_type: Mapped[str] = mapped_column(String)  # deadline/obligation/document/evidence/hearing/order/action
    entity_id: Mapped[str] = mapped_column(String, default="")
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    source_event_id: Mapped[str] = mapped_column(String, default="")


class Conflict(Base):
    __tablename__ = "conflicts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    conflict_type: Mapped[str] = mapped_column(String)
    what_conflicts: Mapped[str] = mapped_column(Text)
    source_a_event_id: Mapped[str] = mapped_column(String)
    source_b_event_id: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    possible_explanation: Mapped[str] = mapped_column(Text, default="")
    human_review_status: Mapped[str] = mapped_column(String, default=ReviewStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Change proposals + human review gate
# ---------------------------------------------------------------------------

class ChangeProposal(Base):
    """
    Output of the Change Detection Agent. An LLM (or the mock provider) may
    PROPOSE a change; it never writes directly to the twin. High-impact or
    ambiguous proposals require human approval before being committed as a
    new StateVersion (see app/agents/orchestrator.py).
    """
    __tablename__ = "change_proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    source_event_id: Mapped[str] = mapped_column(String)
    nature: Mapped[str] = mapped_column(String)  # ChangeNature
    entity_type: Mapped[str] = mapped_column(String)
    proposed_before: Mapped[dict] = mapped_column(JSON, default=dict)
    proposed_after: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    review_status: Mapped[str] = mapped_column(String, default=ReviewStatus.PENDING.value)
    reviewer: Mapped[str] = mapped_column(String, default="")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resulting_version_number: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Verification(Base):
    __tablename__ = "verifications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    change_proposal_id: Mapped[str] = mapped_column(String, default="")
    result: Mapped[str] = mapped_column(String, default=VerificationResult.NOT_RUN.value)
    checks: Mapped[dict] = mapped_column(JSON, default=dict)  # {check_name: bool}
    failure_reasons: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Handoff, Simulation, Agent runs, Audit
# ---------------------------------------------------------------------------

class Handoff(Base):
    __tablename__ = "handoffs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    from_role: Mapped[str] = mapped_column(String)
    to_role: Mapped[str] = mapped_column(String)
    context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft/reviewed/approved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Simulation(Base):
    __tablename__ = "simulations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    base_version_number: Mapped[int] = mapped_column(Integer)
    hypothesis: Mapped[str] = mapped_column(Text)
    result_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    label: Mapped[str] = mapped_column(String, default="SIMULATION ONLY")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, ForeignKey("cases.id"))
    agent_name: Mapped[str] = mapped_column(String)
    correlation_id: Mapped[str] = mapped_column(String, default="")
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, default="")


class AuditEvent(Base):
    """Append-only audit trail across the whole system."""
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now)
    actor: Mapped[str] = mapped_column(String, default="system")
    event_type: Mapped[str] = mapped_column(String)  # ingestion/parsing/extraction/agent_run/proposal/approval/...
    correlation_id: Mapped[str] = mapped_column(String, default="")
    source: Mapped[str] = mapped_column(String, default="")
    result: Mapped[str] = mapped_column(String, default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
