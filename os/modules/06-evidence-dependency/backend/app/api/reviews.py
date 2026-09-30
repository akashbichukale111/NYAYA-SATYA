from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor, require_role
from app.core.case_access import require_case_with_access
from app.models.orm import ReviewTask
from app.models.enums import UserRole
from app.schemas.schemas import ReviewDecision
from app.services.review_service import decide

router = APIRouter()


@router.get("/cases/{case_id}/review-queue")
def review_queue(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    tasks = db.query(ReviewTask).filter(ReviewTask.case_id == case_id).order_by(ReviewTask.created_at.desc()).all()
    return [
        {
            "id": t.id, "action_type": t.action_type, "target_type": t.target_type,
            "target_id": t.target_id, "proposed_change": t.proposed_change,
            "proposing_agent": t.proposing_agent, "status": t.status,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]


def _require_task_with_access(db: Session, review_id: str, actor: Actor) -> ReviewTask:
    task = db.query(ReviewTask).filter(ReviewTask.id == review_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
    require_case_with_access(db, task.case_id, actor)
    return task


@router.post("/reviews/{review_id}/approve")
def approve_review(review_id: str, payload: ReviewDecision, db: Session = Depends(get_db),
                    actor: Actor = Depends(get_actor)):
    _require_task_with_access(db, review_id, actor)
    # Approving a consequential, real change is an ADVOCATE/ADMIN-level decision --
    # this is the Human Legal Gate's role enforcement.
    require_role(actor, UserRole.ADVOCATE.value)
    try:
        task = decide(db, review_id, approve=True, decided_by_user_id=actor.user_id, note=payload.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": task.id, "status": task.status}


@router.post("/reviews/{review_id}/reject")
def reject_review(review_id: str, payload: ReviewDecision, db: Session = Depends(get_db),
                   actor: Actor = Depends(get_actor)):
    _require_task_with_access(db, review_id, actor)
    require_role(actor, UserRole.ADVOCATE.value)
    try:
        task = decide(db, review_id, approve=False, decided_by_user_id=actor.user_id, note=payload.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": task.id, "status": task.status}
