from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.blocker import Blocker
from app.models.requirement import Requirement
from app.models.evidence import Evidence
from app.services import causal_graph
from app.services.explanation_engine import explain_blocker

router = APIRouter(prefix="/api/cases", tags=["blockers"])


@router.get("/{case_id}/blockers")
def list_blockers(case_id: str, db: Session = Depends(get_db)):
    blockers = db.query(Blocker).filter(Blocker.case_id == case_id).all()
    return [b.to_dict() for b in blockers]


@router.get("/{case_id}/blockers/{blocker_id}/why")
def explain(case_id: str, blocker_id: str, db: Session = Depends(get_db)):
    blocker = db.query(Blocker).filter(Blocker.id == blocker_id, Blocker.case_id == case_id).first()
    if not blocker:
        raise HTTPException(404, "Blocker not found")
    req = db.query(Requirement).filter(Requirement.id == blocker.requirement_id).first()
    evidence_items = []
    if req:
        evidence_items = [
            db.query(Evidence).filter(Evidence.id == eid).first() for eid in (req.evidence_refs or [])
        ]
        evidence_items = [e.to_dict() for e in evidence_items if e is not None]
    return explain_blocker(blocker.to_dict(), req.to_dict() if req else {}, evidence_items)


@router.get("/{case_id}/graph")
def get_graph(case_id: str, db: Session = Depends(get_db)):
    return causal_graph.get_graph(db, case_id)


@router.get("/{case_id}/evidence")
def list_evidence(case_id: str, db: Session = Depends(get_db)):
    items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return [e.to_dict() for e in items]
