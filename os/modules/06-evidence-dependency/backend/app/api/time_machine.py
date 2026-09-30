from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import EvidenceItem, Claim
from app.services import time_machine_service as tm

router = APIRouter()


def _require_evidence_with_access(db: Session, evidence_id: str, actor: Actor) -> EvidenceItem:
    item = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    require_case_with_access(db, item.case_id, actor)
    return item


def _require_claim_with_access(db: Session, claim_id: str, actor: Actor) -> Claim:
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_case_with_access(db, claim.case_id, actor)
    return claim


@router.get("/evidence/{evidence_id}/history")
def evidence_history(evidence_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    _require_evidence_with_access(db, evidence_id, actor)
    history = tm.get_history(db, evidence_id)
    return [
        {"version_number": v.version_number, "as_of": v.created_at.isoformat(),
         "reason": v.reason, "snapshot": v.snapshot}
        for v in history
    ]


@router.get("/evidence/{evidence_id}/current-vs-previous")
def evidence_current_vs_previous(evidence_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    _require_evidence_with_access(db, evidence_id, actor)
    return tm.current_vs_previous(db, evidence_id)


@router.get("/evidence/{evidence_id}/diff")
def evidence_diff(evidence_id: str, from_version: int = Query(...), to_version: int = Query(...),
                   db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    _require_evidence_with_access(db, evidence_id, actor)
    v1 = tm.get_version(db, evidence_id, from_version)
    v2 = tm.get_version(db, evidence_id, to_version)
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return tm.diff_versions(v1, v2)


@router.get("/cases/{case_id}/time-machine")
def case_time_machine(case_id: str, at: str = Query(..., description="ISO 8601 timestamp"),
                       db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    try:
        at_dt = datetime.fromisoformat(at)
    except ValueError:
        raise HTTPException(status_code=400, detail="`at` must be an ISO 8601 timestamp")
    return tm.case_state_at(db, case_id, at_dt)


@router.get("/claims/{claim_id}/history")
def claim_history(claim_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    _require_claim_with_access(db, claim_id, actor)
    history = tm.get_claim_history(db, claim_id)
    return [
        {"version_number": v.version_number, "as_of": v.created_at.isoformat(),
         "reason": v.reason, "snapshot": v.snapshot}
        for v in history
    ]


@router.get("/claims/{claim_id}/current-vs-previous")
def claim_current_vs_previous(claim_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    _require_claim_with_access(db, claim_id, actor)
    return tm.claim_current_vs_previous(db, claim_id)


@router.get("/claims/{claim_id}/diff")
def claim_diff(claim_id: str, from_version: int = Query(...), to_version: int = Query(...),
                db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    _require_claim_with_access(db, claim_id, actor)
    v1 = tm.get_claim_version(db, claim_id, from_version)
    v2 = tm.get_claim_version(db, claim_id, to_version)
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    return tm.diff_claim_versions(v1, v2)
