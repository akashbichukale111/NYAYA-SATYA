"""
Human Legal Gate.

Consequential, real (non-simulated) changes to case data must be
proposed as a ReviewTask and require explicit human approve/reject
before being applied. Agents call `propose_action` -- they never
mutate case rows directly. Every proposal and every decision is
written to AuditEvent, which is append-only.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.orm import ReviewTask, AuditEvent, EvidenceItem, Claim, EvidenceRelationship, Conflict
from app.models.enums import ReviewStatus


def propose_action(
    db: Session,
    case_id: str,
    action_type: str,
    target_type: str,
    target_id: str,
    proposed_change: Dict,
    proposing_agent: str = "SYSTEM",
) -> ReviewTask:
    task = ReviewTask(
        id=str(uuid.uuid4()),
        case_id=case_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        proposed_change=proposed_change,
        proposing_agent=proposing_agent,
        status=ReviewStatus.PENDING.value,
        created_at=datetime.utcnow(),
    )
    db.add(task)
    log_audit_event(
        db, case_id, actor=proposing_agent, actor_type="AGENT",
        action=f"PROPOSE_{action_type}", target_type=target_type,
        target_id=target_id, detail={"proposed_change": proposed_change},
    )
    db.commit()
    db.refresh(task)
    return task


def propose_relationship(
    db: Session,
    case_id: str,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    relationship_type: str,
    support_kind: Optional[str] = None,
    explanation: str = "",
    action_type: str = "APPROVE_RELATIONSHIP",
    proposing_agent: str = "SYSTEM",
) -> ReviewTask:
    """Convenience wrapper: agents propose a not-yet-existing relationship
    (e.g. Evidence->Claim SUPPORTS, or Claim->Issue REQUIRES from Issue
    Mapping) through the Human Legal Gate rather than creating it directly."""
    return propose_action(
        db, case_id, action_type=action_type, target_type="RELATIONSHIP_PROPOSAL",
        target_id=str(uuid.uuid4()),
        proposed_change={
            "source_type": source_type, "source_id": source_id,
            "target_type": target_type, "target_id": target_id,
            "relationship_type": relationship_type, "support_kind": support_kind,
            "explanation": explanation,
        },
        proposing_agent=proposing_agent,
    )


def decide(
    db: Session,
    review_id: str,
    approve: bool,
    decided_by_user_id: Optional[str],
    note: str = "",
) -> ReviewTask:
    task = db.query(ReviewTask).filter(ReviewTask.id == review_id).first()
    if not task:
        raise ValueError("Review task not found")
    if task.status != ReviewStatus.PENDING.value:
        raise ValueError(f"Review task already decided: {task.status}")

    task.status = ReviewStatus.APPROVED.value if approve else ReviewStatus.REJECTED.value
    task.decided_by_user_id = decided_by_user_id
    task.decision_note = note
    task.decided_at = datetime.utcnow()

    if approve:
        _apply_change(db, task)

    log_audit_event(
        db, task.case_id, actor=decided_by_user_id or "UNKNOWN_USER", actor_type="USER",
        action="APPROVE_REVIEW" if approve else "REJECT_REVIEW",
        target_type=task.target_type, target_id=task.target_id,
        detail={"review_id": review_id, "note": note},
    )
    db.commit()
    db.refresh(task)
    return task


def _apply_change(db: Session, task: ReviewTask):
    """Apply an approved change. Deliberately narrow -- only known, safe
    field updates are supported; anything else stays PROPOSED-only."""
    change = task.proposed_change or {}

    if task.target_type == "EVIDENCE":
        item = db.query(EvidenceItem).filter(EvidenceItem.id == task.target_id).first()
        if item:
            for field in ("state", "verification_status"):
                if field in change:
                    setattr(item, field, change[field])
            # Every real, human-approved mutation to an evidence item creates a
            # Time Machine snapshot so the change is historically reconstructable.
            from app.services.time_machine_service import snapshot_evidence
            snapshot_evidence(db, item, reason=f"REVIEW_APPROVED:{task.action_type}")

    elif task.target_type == "CLAIM":
        claim = db.query(Claim).filter(Claim.id == task.target_id).first()
        if claim:
            for field in ("verification_status", "review_state", "text"):
                if field in change:
                    setattr(claim, field, change[field])
            from app.services.time_machine_service import snapshot_claim
            snapshot_claim(db, claim, reason=f"REVIEW_APPROVED:{task.action_type}")

    elif task.target_type == "RELATIONSHIP_PROPOSAL":
        # Approving a proposed relationship (e.g. from the Relationship Agent
        # or Issue Mapping Agent) materializes it as a real, active edge.
        rel = EvidenceRelationship(
            case_id=task.case_id,
            source_type=change["source_type"],
            source_id=change["source_id"],
            target_type=change["target_type"],
            target_id=change["target_id"],
            relationship_type=change["relationship_type"],
            support_kind=change.get("support_kind"),
            explanation=change.get("explanation", ""),
            verification_status="VERIFIED",  # human approved it
        )
        db.add(rel)

    elif task.target_type == "RELATIONSHIP":
        rel = db.query(EvidenceRelationship).filter(EvidenceRelationship.id == task.target_id).first()
        if rel:
            for field in ("is_active", "relationship_type", "verification_status"):
                if field in change:
                    setattr(rel, field, change[field])

    elif task.target_type == "CONFLICT":
        conflict = db.query(Conflict).filter(Conflict.id == task.target_id).first()
        if conflict:
            for field in ("status", "description"):
                if field in change:
                    setattr(conflict, field, change[field])


def log_audit_event(
    db: Session,
    case_id: str,
    actor: str,
    action: str,
    actor_type: str = "SYSTEM",
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[Dict] = None,
):
    event = AuditEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        actor=actor,
        actor_type=actor_type,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
        created_at=datetime.utcnow(),
    )
    db.add(event)
    return event
