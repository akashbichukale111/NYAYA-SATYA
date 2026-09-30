from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import Claim
from app.schemas.schemas import ClaimCreate, ClaimOut
from app.services.review_service import log_audit_event
from app.services.time_machine_service import snapshot_claim

router = APIRouter()


@router.post("/cases/{case_id}/claims", response_model=ClaimOut)
def create_claim(case_id: str, payload: ClaimCreate, db: Session = Depends(get_db),
                  actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    claim = Claim(case_id=case_id, text=payload.text, source=payload.source)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    log_audit_event(db, case_id, actor=actor.user_id, actor_type="USER", action="CLAIM_CREATED",
                     target_type="CLAIM", target_id=claim.id)
    snapshot_claim(db, claim, reason="CREATED")
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/cases/{case_id}/claims", response_model=list[ClaimOut])
def list_claims(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return db.query(Claim).filter(Claim.case_id == case_id).all()


@router.get("/claims/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_case_with_access(db, claim.case_id, actor)
    return claim
