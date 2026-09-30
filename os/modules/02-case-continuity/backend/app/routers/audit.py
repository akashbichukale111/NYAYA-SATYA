from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case
from app.agents.audit_agent import get_audit_trail, get_agent_runs

router = APIRouter(prefix="/api/cases", tags=["audit"])


@router.get("/{case_id}/audit")
def case_audit(case_id: str, limit: int = Query(500, le=2000), db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    return {
        "audit_trail": get_audit_trail(db, case_id=case_id, limit=limit),
        "agent_runs": get_agent_runs(db, case_id=case_id, limit=limit),
    }
