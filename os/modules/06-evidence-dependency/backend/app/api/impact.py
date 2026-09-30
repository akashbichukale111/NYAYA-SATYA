from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import EvidenceItem, Claim
from app.services.impact_service import compute_impact

router = APIRouter()


@router.get("/evidence/{evidence_id}/impact")
def evidence_impact(evidence_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    item = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    require_case_with_access(db, item.case_id, actor)
    return compute_impact(db, item.case_id, "EVIDENCE", evidence_id)


@router.get("/claims/{claim_id}/impact")
def claim_impact(claim_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    item = db.query(Claim).filter(Claim.id == claim_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Claim not found")
    require_case_with_access(db, item.case_id, actor)
    return compute_impact(db, item.case_id, "CLAIM", claim_id)
