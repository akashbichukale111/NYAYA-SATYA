from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import Case
from app.models.enums import UserRole
from app.schemas.schemas import CaseCreate, CaseOut
from app.services.review_service import log_audit_event
from app.demo_data.seed import seed_demo_case, DEMO_CASE_SEEDS

router = APIRouter()


@router.post("", response_model=CaseOut)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    case = Case(title=payload.title, description=payload.description, owner_user_id=actor.user_id)
    db.add(case)
    db.commit()
    db.refresh(case)
    log_audit_event(db, case.id, actor=actor.user_id, actor_type="USER", action="CASE_CREATED",
                     target_type="CASE", target_id=case.id)
    db.commit()
    return case


@router.get("", response_model=list[CaseOut])
def list_cases(db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    """Cases owned by the actor, plus demo cases and legacy/open cases. ADMIN sees all."""
    all_cases = db.query(Case).order_by(Case.created_at.desc()).all()
    if actor.role == UserRole.ADMIN.value:
        return all_cases
    return [
        c for c in all_cases
        if c.is_demo or c.owner_user_id is None or c.owner_user_id == actor.user_id
    ]


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return require_case_with_access(db, case_id, actor)


@router.post("/demo/seed/{demo_key}", response_model=CaseOut)
def seed_demo(demo_key: str, db: Session = Depends(get_db)):
    """Seed one of the deterministic offline demo cases (A/B/C). No API key required.
    Demo cases are intentionally open (is_demo=True bypasses ownership checks)."""
    if demo_key not in DEMO_CASE_SEEDS:
        raise HTTPException(status_code=404, detail=f"Unknown demo case '{demo_key}'. Known: {list(DEMO_CASE_SEEDS)}")
    case = seed_demo_case(db, demo_key)
    return case
