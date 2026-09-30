from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case
from app.agents.timeline_agent import build_timeline
from app.agents.base import new_correlation_id

router = APIRouter(prefix="/api/cases", tags=["timeline"])


@router.get("/{case_id}/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    return build_timeline(db, case_id=case_id, correlation_id=new_correlation_id())
