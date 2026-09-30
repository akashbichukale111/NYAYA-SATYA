from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.case import Case
from app.schemas.api_schemas import CaseCreate
from app.services import case_twin, audit_service
from app.agents.orchestrator import run_readiness_pass

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    return [c.to_dict() for c in cases]


@router.post("")
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = case_twin.create_case(db, payload.title, payload.case_type, payload.parties, is_synthetic=False)
    db.commit()
    return case.to_dict()


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    full = case_twin.get_case_full(db, case_id)
    if not full:
        raise HTTPException(404, "Case not found")
    return full


@router.post("/{case_id}/run-agent-pass")
def run_agent_pass(case_id: str, db: Session = Depends(get_db)):
    full = case_twin.get_case_full(db, case_id)
    if not full:
        raise HTTPException(404, "Case not found")
    run = run_readiness_pass(db, case_id)
    db.commit()
    return run.to_dict()
