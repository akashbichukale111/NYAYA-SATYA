from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import case_twin, readiness_engine

router = APIRouter(prefix="/api/cases", tags=["readiness"])


@router.get("/{case_id}/readiness")
def get_readiness(case_id: str, db: Session = Depends(get_db)):
    full = case_twin.get_case_full(db, case_id)
    if not full:
        raise HTTPException(404, "Case not found")
    hearing = next((h for h in full["hearings"] if h["is_next"] == "true"), None)
    hearing_uncertain = (hearing is None) or (hearing["purpose_status"] == "UNCERTAIN")
    return readiness_engine.build_readiness_snapshot(
        full["requirements"], full["blockers"], hearing_uncertain
    )


@router.post("/{case_id}/readiness/run")
def run_audit(case_id: str, db: Session = Depends(get_db)):
    full = case_twin.get_case_full(db, case_id)
    if not full:
        raise HTTPException(404, "Case not found")
    snapshot = readiness_engine.run_readiness_audit(db, case_id)
    db.commit()
    return snapshot
