from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, Party
from app.state_twin import build_snapshot
from app.freshness import compute_freshness
from app.agents.orchestrator import initialize_case_v0
from app.audit import log_audit

router = APIRouter(prefix="/api/cases", tags=["cases"])


class PartyIn(BaseModel):
    name: str
    role: str = ""
    representative: str = ""


class CaseCreate(BaseModel):
    title: str
    case_number: str = ""
    court: str = ""
    parties: list[PartyIn] = []


@router.get("")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    out = []
    for c in cases:
        freshness = compute_freshness(db, c.id)
        out.append({
            "id": c.id, "title": c.title, "case_number": c.case_number, "court": c.court,
            "procedural_stage": c.procedural_stage, "is_demo": c.is_demo, "demo_case_key": c.demo_case_key,
            "created_at": c.created_at.isoformat(), "current_version_number": c.current_version_number,
            "freshness": freshness["level"],
        })
    return out


@router.post("")
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = Case(title=payload.title, case_number=payload.case_number, court=payload.court)
    db.add(case)
    db.commit()
    db.refresh(case)
    for p in payload.parties:
        db.add(Party(case_id=case.id, name=p.name, role=p.role, representative=p.representative))
    db.commit()
    initialize_case_v0(db, case_id=case.id, actor="user")
    log_audit(db, case_id=case.id, actor="user", event_type="user_action", source="create_case", result="ok")
    return {"id": case.id, "title": case.title}


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    parties = db.query(Party).filter(Party.case_id == case_id).all()
    return {
        "id": case.id, "title": case.title, "case_number": case.case_number, "court": case.court,
        "procedural_stage": case.procedural_stage, "is_demo": case.is_demo, "demo_case_key": case.demo_case_key,
        "created_at": case.created_at.isoformat(), "current_version_number": case.current_version_number,
        "parties": [{"id": p.id, "name": p.name, "role": p.role, "representative": p.representative} for p in parties],
    }
