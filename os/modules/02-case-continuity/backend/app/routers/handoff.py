from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, Handoff
from app.agents.context_agent import build_handoff_context
from app.agents.base import new_correlation_id
from app.audit import log_audit
from datetime import datetime, timezone

router = APIRouter(prefix="/api/cases", tags=["handoff"])


class HandoffCreate(BaseModel):
    from_role: str
    to_role: str


class HandoffApprove(BaseModel):
    reviewer: str = "user"


@router.post("/{case_id}/handoff")
def prepare_handoff(case_id: str, payload: HandoffCreate, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    context = build_handoff_context(db, case_id=case_id, correlation_id=new_correlation_id())
    handoff = Handoff(
        case_id=case_id, from_role=payload.from_role, to_role=payload.to_role,
        context_snapshot=context, status="draft",
    )
    db.add(handoff)
    db.commit()
    db.refresh(handoff)
    return {"id": handoff.id, "status": handoff.status, "context": context}


@router.get("/{case_id}/handoff/{handoff_id}")
def get_handoff(case_id: str, handoff_id: str, db: Session = Depends(get_db)):
    h = db.get(Handoff, handoff_id)
    if not h or h.case_id != case_id:
        raise HTTPException(404, "handoff not found")
    return {
        "id": h.id, "from_role": h.from_role, "to_role": h.to_role, "status": h.status,
        "context": h.context_snapshot, "created_at": h.created_at.isoformat(),
    }


@router.post("/{case_id}/handoff/{handoff_id}/approve")
def approve_handoff(case_id: str, handoff_id: str, payload: HandoffApprove, db: Session = Depends(get_db)):
    h = db.get(Handoff, handoff_id)
    if not h or h.case_id != case_id:
        raise HTTPException(404, "handoff not found")
    h.status = "approved"
    h.approved_at = datetime.now(timezone.utc)
    db.commit()
    log_audit(db, case_id=case_id, actor=payload.reviewer, event_type="user_action",
               source=handoff_id, result="handoff_approved")
    return {"id": h.id, "status": h.status}
