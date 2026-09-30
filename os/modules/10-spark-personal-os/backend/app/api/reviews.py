from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, ReviewTask
from app.schemas.schemas import ReviewTaskOut, ReviewDecision
from app.core.security import get_current_user
from app.services.access import authorized_case_ids
from app.services.audit import log_audit

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("", response_model=list[ReviewTaskOut])
def my_reviews(case_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids:
        return []
    q = db.query(ReviewTask).filter(ReviewTask.case_id.in_(ids))
    if case_id:
        q = q.filter(ReviewTask.case_id == case_id)
    return q.order_by(ReviewTask.created_at.desc()).all()


@router.post("/{review_id}/decide", response_model=ReviewTaskOut)
def decide_review(
    review_id: str, payload: ReviewDecision,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    review = db.get(ReviewTask, review_id)
    ids = authorized_case_ids(db, user)
    if review is None or review.case_id not in ids:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = payload.status
    review.decided_by = user.id
    review.decided_at = datetime.utcnow()
    review.decision_note = payload.decision_note
    db.commit()
    db.refresh(review)
    log_audit(db, actor_user_id=user.id, action=f"review.{payload.status.value}",
              target_type="ReviewTask", target_id=review.id,
              detail={"kind": review.kind.value, "note": payload.decision_note})
    return review
