from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_capability, assert_case_access
from app.core.ids import utcnow
from app.core.audit import record as audit_record
from app import models, schemas
from app.routers.cases import _get_package_or_404

router = APIRouter(tags=["review"])


@router.get("/api/filing-packages/{package_id}/review-queue", response_model=list[schemas.ReviewTaskOut])
def get_review_queue(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    return db.query(models.ReviewTask).filter(
        models.ReviewTask.filing_package_id == package_id,
        models.ReviewTask.decision == "PENDING",
    ).all()


def _apply_decision(db: Session, review: models.ReviewTask, user: models.User, decision: str, reason: str | None):
    before = {"decision": review.decision}
    review.decision = decision
    review.decided_by_user_id = user.id
    review.decided_at = utcnow().isoformat()
    review.reason = reason

    # Apply the human decision to the underlying entity. This is the ONLY
    # code path that can move a Defect out of DETECTED/system-only states.
    if review.target_type == "DEFECT":
        defect = db.query(models.Defect).filter(models.Defect.id == review.target_id).first()
        if defect:
            if review.action_requested == "CONFIRM_RESOLUTION_AFTER_VERIFICATION":
                if decision == "APPROVED":
                    defect.status = "RESOLVED"
                    defect.resolution_note = reason or "Confirmed resolved by human reviewer after verification."
                    defect.resolved_at = utcnow().isoformat()
                    defect.human_review_required = False
                # REJECTED here means the human disagrees a re-verified
                # defect is actually fixed; it goes back to HUMAN_REVIEW
                # rather than being discarded.
                else:
                    defect.status = "HUMAN_REVIEW"
            else:
                defect.status = "CONFIRMED" if decision == "APPROVED" else "REJECTED"
                defect.verification_status = "REQUIRES_HUMAN_REVIEW" if decision == "APPROVED" else defect.verification_status
                if decision == "REJECTED":
                    defect.human_review_required = False
                    defect.resolution_note = reason or "Rejected by human reviewer as false positive or not applicable."

    db.commit()

    audit_record(
        db, case_id=review.case_id, actor_user_id=user.id, actor_role=user.role,
        action=f"REVIEW_{decision}", entity_type=review.target_type, entity_id=review.target_id,
        before_state=before, after_state={"decision": decision, "reason": reason},
        reason=reason, provenance="HUMAN_DECISION",
    )


@router.post("/api/reviews/{review_id}/approve", response_model=schemas.ReviewTaskOut)
def approve_review(review_id: str, payload: schemas.ReviewDecisionIn, db: Session = Depends(get_db),
                    user: models.User = Depends(get_current_user)):
    review = db.query(models.ReviewTask).filter(models.ReviewTask.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review task not found")
    assert_case_access(db, user, review.case_id)
    require_capability(user, "APPROVE_REVIEW")
    _apply_decision(db, review, user, "APPROVED", payload.reason)
    db.refresh(review)
    return review


@router.post("/api/reviews/{review_id}/reject", response_model=schemas.ReviewTaskOut)
def reject_review(review_id: str, payload: schemas.ReviewDecisionIn, db: Session = Depends(get_db),
                   user: models.User = Depends(get_current_user)):
    review = db.query(models.ReviewTask).filter(models.ReviewTask.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review task not found")
    assert_case_access(db, user, review.case_id)
    require_capability(user, "REJECT_REVIEW")
    _apply_decision(db, review, user, "REJECTED", payload.reason)
    db.refresh(review)
    return review


@router.get("/api/filing-packages/{package_id}/audit", response_model=list[schemas.AuditEventOut])
def get_audit_trail(package_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    package = _get_package_or_404(db, package_id)
    assert_case_access(db, user, package.case_id)
    require_capability(user, "VIEW_AUDIT")
    return db.query(models.AuditEvent).filter(models.AuditEvent.case_id == package.case_id).order_by(
        models.AuditEvent.timestamp.desc()
    ).all()
