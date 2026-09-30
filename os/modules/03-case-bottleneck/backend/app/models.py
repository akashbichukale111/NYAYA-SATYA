"""
Domain models — Case Bottleneck Engine.

NOTE ON SCOPE (see README > Limitations):
The full spec lists 18 separate entities (Case, CaseState, Event, Document,
Evidence, Transition, Requirement, Dependency, Bottleneck, RootCauseCandidate,
Investigation, Action, Approval, Verification, Simulation, BottleneckHistory,
AgentRun, AuditEvent). For a buildable, testable hackathon-scope system we
have consolidated some of these:

  - CaseState + Event                -> CaseEvent
  - Requirement + Transition         -> Transition (prerequisites embedded)
  - Evidence                          -> embedded in Dependency/CaseDocument
  - Investigation + AgentRun          -> AuditEvent (correlation_id groups a run)
  - Approval                          -> fields on ActionItem
  - Simulation                        -> not persisted; computed on demand and
                                         returned directly (SIMULATION ONLY,
                                         never written to case state)

This is a deliberate simplification, not a hidden shortcut — it is documented
here and in the README so nobody mistakes it for the full 18-table design.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field, JSON, Column


def utcnow() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Enums (per spec taxonomies — Sections 4, 5, 13, 15)
# ---------------------------------------------------------------------------

class BottleneckType(str, Enum):
    DOCUMENT_BLOCKER = "DOCUMENT_BLOCKER"
    FILING_BLOCKER = "FILING_BLOCKER"
    SERVICE_BLOCKER = "SERVICE_BLOCKER"
    RESPONSE_BLOCKER = "RESPONSE_BLOCKER"
    EVIDENCE_BLOCKER = "EVIDENCE_BLOCKER"
    PROCEDURAL_BLOCKER = "PROCEDURAL_BLOCKER"
    ORDER_COMPLIANCE_BLOCKER = "ORDER_COMPLIANCE_BLOCKER"
    DEADLINE_BLOCKER = "DEADLINE_BLOCKER"
    DEPENDENCY_BLOCKER = "DEPENDENCY_BLOCKER"
    ACTOR_DEPENDENCY = "ACTOR_DEPENDENCY"
    VERIFICATION_BLOCKER = "VERIFICATION_BLOCKER"
    CONTRADICTION_BLOCKER = "CONTRADICTION_BLOCKER"
    STATE_FRESHNESS_BLOCKER = "STATE_FRESHNESS_BLOCKER"
    INFORMATION_GAP = "INFORMATION_GAP"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    UNKNOWN_BLOCKER = "UNKNOWN_BLOCKER"


class ConfidenceLabel(str, Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


class AttentionState(str, Enum):
    CRITICAL = "CRITICAL ATTENTION"
    HIGH = "HIGH ATTENTION"
    NORMAL = "NORMAL"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class BottleneckStatus(str, Enum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"
    ACTIONABLE = "ACTIONABLE"
    ACTION_PENDING_APPROVAL = "ACTION_PENDING_APPROVAL"
    ACTION_APPROVED = "ACTION_APPROVED"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class DependencyStatus(str, Enum):
    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


# ---------------------------------------------------------------------------
# Core case data (the "Case Digital Twin" surface this engine consumes)
# ---------------------------------------------------------------------------

class Case(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str
    case_type: str
    description: str = ""
    is_demo: bool = True
    demo_scenario: Optional[str] = None  # e.g. "A".."J"
    created_at: datetime = Field(default_factory=utcnow)


class CaseEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    event_type: str
    description: str
    occurred_at: datetime
    verified: bool = False
    document_ref: Optional[str] = None


class CaseDocument(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    name: str
    content_text: str = ""
    uploaded_at: datetime = Field(default_factory=utcnow)
    contains_injection_attempt: bool = False
    quarantined: bool = False
    sha256: Optional[str] = None


class Dependency(SQLModel, table=True):
    """A node in the case's dependency graph (Section 6/8)."""
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    description: str
    type: str  # free text label, e.g. "document", "service", "evidence"
    status: DependencyStatus = DependencyStatus.UNKNOWN
    depends_on: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    evidence_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    since: Optional[datetime] = None
    note: str = ""


class Transition(SQLModel, table=True):
    """A pending workflow transition and the dependencies that gate it (Requirement folded in)."""
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    name: str
    prerequisite_dependency_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = "PENDING"  # PENDING | READY | COMPLETED


# ---------------------------------------------------------------------------
# Bottleneck domain (Sections 4, 7, 15)
# ---------------------------------------------------------------------------

class Bottleneck(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    type: BottleneckType
    description: str
    root_cause_candidate: str = ""
    evidence_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    dependency_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    affected_transitions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    blocked_items: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    responsible_actor_if_known: Optional[str] = None
    first_observed_at: datetime = Field(default_factory=utcnow)
    last_confirmed_at: datetime = Field(default_factory=utcnow)
    last_updated_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None
    severity_factors: dict = Field(default_factory=dict, sa_column=Column(JSON))
    attention_state: AttentionState = AttentionState.UNKNOWN
    confidence: ConfidenceLabel = ConfidenceLabel.UNKNOWN
    status: BottleneckStatus = BottleneckStatus.DETECTED
    verification_state: str = "NOT_VERIFIED"
    contradicting_evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    missing_evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    recurrence_count: int = 0


class RootCauseCandidate(SQLModel, table=True):
    id: str = Field(primary_key=True)
    bottleneck_id: str = Field(foreign_key="bottleneck.id", index=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    chain: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    confidence: ConfidenceLabel = ConfidenceLabel.UNKNOWN
    is_primary: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class ActionItem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    bottleneck_id: str = Field(foreign_key="bottleneck.id", index=True)
    action_type: str
    purpose: str
    required_actor: str
    status: ActionStatus = ActionStatus.PENDING_APPROVAL
    expected_effect: str = ""
    risk: str = "LOW"
    verification_method: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))
    rejection_reason: Optional[str] = None


class VerificationRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    action_id: str = Field(foreign_key="actionitem.id", index=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    passed: bool
    checked_at: datetime = Field(default_factory=utcnow)
    details: str = ""


class BottleneckHistoryEntry(SQLModel, table=True):
    id: str = Field(primary_key=True)
    bottleneck_id: str = Field(foreign_key="bottleneck.id", index=True)
    case_id: str = Field(foreign_key="case.id", index=True)
    from_status: str
    to_status: str
    timestamp: datetime = Field(default_factory=utcnow)
    note: str = ""


class AuditEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    correlation_id: str = Field(index=True)
    actor: str
    event: str
    source: str
    result: dict = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=utcnow)
