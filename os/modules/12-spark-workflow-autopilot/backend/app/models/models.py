import uuid
import datetime as dt

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Boolean, Text, JSON
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.enums import (
    WorkflowState, TaskState, RiskLevel, ApprovalState, VerificationState,
)


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=lambda: gen_id("case"))
    title = Column(String, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    state_version = Column(Integer, default=1, nullable=False)  # bumped on any case-state change -> stale-state protection
    owner_user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    workflows = relationship("Workflow", back_populates="case", cascade="all, delete-orphan")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: gen_id("wf"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    workflow_type = Column(String, nullable=False)          # e.g. "evidence_gap"
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    trigger_type = Column(String, nullable=False)
    trigger_source_engine = Column(String, nullable=True)
    trigger_event_id = Column(String, nullable=True)        # for idempotency
    status = Column(String, default=WorkflowState.DRAFT.value, nullable=False)
    priority = Column(String, default="NORMAL")
    risk_level = Column(String, default=RiskLevel.LOW_RISK.value)
    approval_state = Column(String, default=ApprovalState.NOT_REQUIRED.value)
    verification_state = Column(String, default=VerificationState.NOT_REQUIRED.value)
    case_state_version_at_creation = Column(Integer, nullable=False, default=1)
    created_by = Column(String, default="system")
    provenance_id = Column(String, default=lambda: gen_id("prov"))
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    case = relationship("Case", back_populates="workflows")
    tasks = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: gen_id("task"))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    task_type = Column(String, default="generic")
    owner_role = Column(String, default="PARALEGAL")
    status = Column(String, default=TaskState.TODO.value, nullable=False)
    priority = Column(String, default="NORMAL")
    sequence_index = Column(Integer, default=0)              # order within the template
    input_requirements = Column(JSON, default=list)
    expected_output = Column(Text, default="")
    approval_required = Column(Boolean, default=False)
    verification_required = Column(Boolean, default=False)
    risk_level = Column(String, default=RiskLevel.SAFE_REVERSIBLE.value)
    failure_reason = Column(Text, nullable=True)
    provenance_id = Column(String, default=lambda: gen_id("prov"))
    created_at = Column(DateTime, default=now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="tasks")
    dependencies_out = relationship(
        "Dependency", foreign_keys="Dependency.task_id", back_populates="task",
        cascade="all, delete-orphan",
    )


class Dependency(Base):
    """task_id depends_on depends_on_task_id (depends_on must satisfy `kind` before task_id may become READY)."""
    __tablename__ = "dependencies"

    id = Column(String, primary_key=True, default=lambda: gen_id("dep"))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    depends_on_task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    kind = Column(String, default="BLOCKING")  # BLOCKING | CONDITIONAL | VERIFICATION | APPROVAL
    created_at = Column(DateTime, default=now)

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies_out")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True, default=lambda: gen_id("appr"))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    action_description = Column(Text, nullable=False)
    reason = Column(Text, default="")
    previous_state = Column(String, nullable=True)
    requested_state = Column(String, nullable=True)
    risk_level = Column(String, default=RiskLevel.APPROVAL_REQUIRED.value)
    state = Column(String, default=ApprovalState.PENDING.value)
    requested_by = Column(String, default="system")
    decided_by = Column(String, nullable=True)
    decision_reason = Column(Text, nullable=True)
    provenance_id = Column(String, default=lambda: gen_id("prov"))
    created_at = Column(DateTime, default=now)
    decided_at = Column(DateTime, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=lambda: gen_id("evt"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    workflow_id = Column(String, nullable=True)
    task_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    actor = Column(String, default="system")
    payload = Column(JSON, default=dict)
    provenance_id = Column(String, default=lambda: gen_id("prov"))
    created_at = Column(DateTime, default=now)


class ProcessedEvent(Base):
    """Idempotency ledger: one row per external trigger event_id ever accepted."""
    __tablename__ = "processed_events"

    event_id = Column(String, primary_key=True)
    workflow_id = Column(String, nullable=True)
    processed_at = Column(DateTime, default=now)


class ConflictRecord(Base):
    """Preserved record of two workflow signals that conflict, awaiting human resolution."""
    __tablename__ = "conflict_records"

    id = Column(String, primary_key=True, default=lambda: gen_id("conflict"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    workflow_id_a = Column(String, nullable=False)
    workflow_id_b = Column(String, nullable=False)
    signal_a = Column(Text, nullable=False)
    signal_b = Column(Text, nullable=False)
    status = Column(String, default="OPEN")  # OPEN | RESOLVED
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String, nullable=True)
    provenance_id = Column(String, default=lambda: gen_id("prov"))
    created_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime, nullable=True)
