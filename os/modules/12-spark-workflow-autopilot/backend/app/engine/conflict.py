"""
Conflict handling.

When two engines emit signals whose implied actions compete (e.g. one says
"prepare to file" while another says "required document unavailable"), the
system must not blindly proceed with either. Both signals are preserved and
a ConflictRecord is created for human review; new workflow creation is not
blocked, but resolving it is a human decision, not an engine guess.
"""
from sqlalchemy.orm import Session

from app.models.models import Workflow, ConflictRecord
from app.core.enums import WorkflowState, EventType
from app.engine.audit import record_event

# Trigger-type pairs whose implied actions are known to compete operationally.
# This is deliberately a small, explicit, human-curated list — never inferred.
COMPETING_TRIGGER_PAIRS = {
    frozenset({"TRACKED_DATE_APPROACHING", "REGISTRY_DEFECT_DETECTED"}),
    frozenset({"TRACKED_DATE_APPROACHING", "NEW_EVIDENCE_GAP"}),
    frozenset({"HEARING_READINESS_BLOCKER", "REGISTRY_DEFECT_DETECTED"}),
    frozenset({"OBLIGATION_BLOCKED", "TRACKED_DATE_APPROACHING"}),
}

ACTIVE_STATES = {
    WorkflowState.DRAFT.value, WorkflowState.PLANNED.value, WorkflowState.REVIEW_REQUIRED.value,
    WorkflowState.APPROVAL_REQUIRED.value, WorkflowState.APPROVED.value, WorkflowState.READY.value,
    WorkflowState.RUNNING.value, WorkflowState.WAITING.value, WorkflowState.BLOCKED.value,
    WorkflowState.PARTIALLY_COMPLETED.value, WorkflowState.VERIFICATION_PENDING.value,
}


def detect_conflicts(db: Session, case_id: str, new_workflow: Workflow) -> list:
    """
    Called right after a workflow is planned. Looks for other active workflows
    on the same case whose trigger type competes with the new one. Creates and
    returns any new ConflictRecord objects (does not resolve them).
    """
    others = (
        db.query(Workflow)
        .filter(Workflow.case_id == case_id, Workflow.id != new_workflow.id, Workflow.status.in_(ACTIVE_STATES))
        .all()
    )
    created = []
    for other in others:
        pair = frozenset({new_workflow.trigger_type, other.trigger_type})
        if pair in COMPETING_TRIGGER_PAIRS:
            existing = (
                db.query(ConflictRecord)
                .filter(
                    ConflictRecord.case_id == case_id,
                    ConflictRecord.status == "OPEN",
                    ConflictRecord.workflow_id_a.in_([new_workflow.id, other.id]),
                    ConflictRecord.workflow_id_b.in_([new_workflow.id, other.id]),
                )
                .first()
            )
            if existing:
                continue
            record = ConflictRecord(
                case_id=case_id,
                workflow_id_a=new_workflow.id,
                workflow_id_b=other.id,
                signal_a=f"{new_workflow.trigger_type}: {new_workflow.title}",
                signal_b=f"{other.trigger_type}: {other.title}",
            )
            db.add(record)
            db.flush()
            record_event(db, case_id, EventType.CONFLICT_DETECTED.value, "system",
                         workflow_id=new_workflow.id, payload={
                             "conflict_id": record.id, "with_workflow": other.id,
                             "signal_a": record.signal_a, "signal_b": record.signal_b,
                         })
            created.append(record)
    return created


def resolve_conflict(db: Session, conflict_id: str, resolved_by: str, resolution: str) -> ConflictRecord:
    import datetime as dt
    record = db.query(ConflictRecord).filter(ConflictRecord.id == conflict_id).first()
    if record is None:
        raise ValueError(f"conflict {conflict_id} not found")
    if resolved_by == "system":
        raise ValueError("system cannot resolve a conflict on its own behalf; a human must decide")
    record.status = "RESOLVED"
    record.resolution = resolution
    record.resolved_by = resolved_by
    record.resolved_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(record)
    return record
