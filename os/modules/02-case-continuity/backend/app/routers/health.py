from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case
from app.continuity_health import compute_continuity_health

router = APIRouter(prefix="/api/cases", tags=["health"])


@router.get("/{case_id}/continuity-health")
def continuity_health(case_id: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    return compute_continuity_health(db, case_id)
