from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, Conflict
from app.audit import log_audit

router = APIRouter(prefix="/api/cases", tags=["conflicts"])


class ConflictReview(BaseModel):
    resolution_note: str = ""
    reviewer: str = "user"


@router.get("/{case_id}/conflicts")
def list_conflicts(case_id: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    conflicts = db.query(Conflict).filter(Conflict.case_id == case_id).order_by(Conflict.created_at.desc()).all()
    return [
        {
            "id": c.id, "conflict_type": c.conflict_type, "what_conflicts": c.what_conflicts,
            "source_a_event_id": c.source_a_event_id, "source_b_event_id": c.source_b_event_id,
            "confidence": c.confidence, "possible_explanation": c.possible_explanation,
            "human_review_status": c.human_review_status, "created_at": c.created_at.isoformat(),
        }
        for c in conflicts
    ]


@router.post("/{case_id}/conflicts/{conflict_id}/resolve")
def resolve_conflict(case_id: str, conflict_id: str, payload: ConflictReview, db: Session = Depends(get_db)):
    conflict = db.get(Conflict, conflict_id)
    if not conflict or conflict.case_id != case_id:
        raise HTTPException(404, "conflict not found")
    conflict.human_review_status = "resolved"
    db.commit()
    log_audit(db, case_id=case_id, actor=payload.reviewer, event_type="user_action",
               source=conflict_id, result="conflict_resolved", detail={"note": payload.resolution_note})
    return {"status": "resolved", "conflict_id": conflict_id}
