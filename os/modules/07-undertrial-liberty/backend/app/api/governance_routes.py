from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import orm
from app.core.security import (
    get_current_user, CurrentUser, get_case_or_404, require_min_role,
    REVIEW_DECISION_MIN_ROLE,
)
from app.agents.governance import decide_review_task, log_audit_event, record_verification
from app.models.schemas import ReviewDecision

router = APIRouter(prefix="/api", tags=["governance"])


def _ser(row, fields):
    return {f: getattr(row, f, None) for f in fields}


@router.get("/cases/{case_id}/attention")
def get_attention(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "category", "severity", "reason", "source_refs", "status",
              "requires_human_review", "related_entity_type", "related_entity_id", "created_at"]
    rows = db.query(orm.AttentionItem).filter(
        orm.AttentionItem.case_id == case_id, orm.AttentionItem.status == "OPEN"
    ).order_by(orm.AttentionItem.severity.desc()).all()
    return {"attention_items": [_ser(r, fields) for r in rows]}


@router.get("/cases/{case_id}/dependency-graph")
def get_dependency_graph(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    edges = db.query(orm.Dependency).filter(orm.Dependency.case_id == case_id).all()
    fields = ["id", "dependency_type", "from_entity_type", "from_entity_id", "to_entity_type",
              "to_entity_id", "status", "source_document_id"]
    return {"edges": [_ser(e, fields) for e in edges]}


@router.get("/cases/{case_id}/conflicts")
def get_conflicts(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "entity_type", "field_name", "source_a_ref", "source_b_ref",
              "value_a", "value_b", "status", "resolved_value", "resolved_by_user_id", "created_at"]
    rows = db.query(orm.Conflict).filter(orm.Conflict.case_id == case_id).all()
    return {"conflicts": [_ser(r, fields) for r in rows]}


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, resolved_value: str, note: str = "",
                      db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, REVIEW_DECISION_MIN_ROLE)
    conflict = db.query(orm.Conflict).filter(orm.Conflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    from datetime import datetime, timezone
    conflict.status = "RESOLVED_BY_HUMAN"
    conflict.resolved_value = resolved_value
    conflict.resolved_by_user_id = user.user_id
    conflict.resolved_at = datetime.now(timezone.utc)
    db.commit()
    log_audit_event(db, conflict.case_id, user.user_id, "UPDATE", "Conflict", conflict.id,
                     {"resolved_value": resolved_value, "note": note})
    return {"status": "resolved", "conflict_id": conflict.id}


@router.get("/cases/{case_id}/verification")
def get_verification(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "entity_type", "entity_id", "verification_status",
              "verified_by_user_id", "note", "created_at"]
    rows = db.query(orm.Verification).filter(orm.Verification.case_id == case_id).all()
    return {"verifications": [_ser(r, fields) for r in rows]}


@router.post("/cases/{case_id}/verification")
def post_verification(case_id: str, entity_type: str, entity_id: str, verification_status: str,
                       note: str = "", db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, REVIEW_DECISION_MIN_ROLE)
    get_case_or_404(db, case_id)
    v = record_verification(db, case_id, entity_type, entity_id, verification_status, user.user_id, note)
    log_audit_event(db, case_id, user.user_id, "UPDATE", entity_type, entity_id,
                     {"verification_status": verification_status})
    return {"id": v.id, "status": "recorded"}


@router.get("/cases/{case_id}/review-queue")
def get_review_queue(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "task_type", "description", "related_entity_type", "related_entity_id",
              "status", "proposed_change", "decided_by_user_id", "decided_at", "decision_note", "created_at"]
    rows = db.query(orm.ReviewTask).filter(orm.ReviewTask.case_id == case_id).order_by(
        orm.ReviewTask.created_at.desc()).all()
    return {"review_tasks": [_ser(r, fields) for r in rows]}


@router.post("/reviews/{review_id}/approve")
def approve_review(review_id: str, payload: ReviewDecision, db: Session = Depends(get_db),
                    user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, REVIEW_DECISION_MIN_ROLE)
    task = decide_review_task(db, review_id, True, user.user_id, payload.note)
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
    return {"id": task.id, "status": task.status}


@router.post("/reviews/{review_id}/reject")
def reject_review(review_id: str, payload: ReviewDecision, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, REVIEW_DECISION_MIN_ROLE)
    task = decide_review_task(db, review_id, False, user.user_id, payload.note)
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
    return {"id": task.id, "status": task.status}


@router.get("/cases/{case_id}/audit")
def get_audit(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    fields = ["id", "case_id", "actor_user_id", "action", "entity_type", "entity_id", "details", "created_at"]
    rows = db.query(orm.AuditEvent).filter(orm.AuditEvent.case_id == case_id).order_by(
        orm.AuditEvent.created_at.desc()).all()
    return {"audit_events": [_ser(r, fields) for r in rows]}
