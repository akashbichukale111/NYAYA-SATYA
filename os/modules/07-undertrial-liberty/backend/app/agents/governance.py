"""
Audit Agent, Verification Agent, and Human Review Gate.

Any action listed in ACTIONS_REQUIRING_REVIEW must go through a ReviewTask
rather than being applied directly. The audit log is append-only from the
application's perspective (no update/delete endpoints are exposed for it).
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models import orm
from app.core.enums import ReviewTaskStatus, VerificationStatus


def log_audit_event(db: Session, case_id: Optional[str], actor_user_id: Optional[str], action: str,
                     entity_type: Optional[str] = None, entity_id: Optional[str] = None,
                     details: Optional[dict] = None):
    event = orm.AuditEvent(
        case_id=case_id, actor_user_id=actor_user_id, action=action,
        entity_type=entity_type, entity_id=entity_id, details=details or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


ACTIONS_REQUIRING_REVIEW = {
    "CUSTODY_STATE_CORRECTION", "CONFLICT_RESOLUTION", "VERIFICATION_STATUS_CHANGE",
    "RELEASE_VERIFICATION", "ORDER_INTERPRETATION", "EVENT_CORRECTION",
    "SENSITIVE_DATA_ACCESS", "EXPORT_APPROVAL",
}


def create_review_task(db: Session, case_id: str, task_type: str, description: str,
                        related_entity_type: Optional[str] = None, related_entity_id: Optional[str] = None,
                        proposed_change: Optional[dict] = None) -> orm.ReviewTask:
    task = orm.ReviewTask(
        case_id=case_id, task_type=task_type, description=description,
        related_entity_type=related_entity_type, related_entity_id=related_entity_id,
        status=ReviewTaskStatus.PENDING.value, proposed_change=proposed_change,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def decide_review_task(db: Session, review_id: str, approve: bool, decided_by_user_id: str,
                        decision_note: Optional[str] = None) -> orm.ReviewTask:
    task = db.query(orm.ReviewTask).filter(orm.ReviewTask.id == review_id).first()
    if not task:
        return None
    task.status = ReviewTaskStatus.APPROVED.value if approve else ReviewTaskStatus.REJECTED.value
    task.decided_by_user_id = decided_by_user_id
    task.decided_at = datetime.now(timezone.utc)
    task.decision_note = decision_note
    db.commit()
    db.refresh(task)
    log_audit_event(
        db, task.case_id, decided_by_user_id, "APPROVE" if approve else "REJECT",
        entity_type="ReviewTask", entity_id=task.id,
        details={"task_type": task.task_type, "note": decision_note},
    )
    return task


def record_verification(db: Session, case_id: str, entity_type: str, entity_id: str,
                         verification_status: str, verified_by_user_id: Optional[str] = None,
                         note: Optional[str] = None) -> orm.Verification:
    v = orm.Verification(
        case_id=case_id, entity_type=entity_type, entity_id=entity_id,
        verification_status=verification_status, verified_by_user_id=verified_by_user_id, note=note,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v
