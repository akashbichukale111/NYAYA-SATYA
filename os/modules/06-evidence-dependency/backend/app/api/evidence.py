from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor, require_case_access
from app.core.case_access import require_case_with_access
from app.models.orm import EvidenceItem
from app.schemas.schemas import EvidenceCreate, EvidenceOut
from app.services.review_service import log_audit_event
from app.services.time_machine_service import snapshot_evidence

router = APIRouter()


@router.post("/cases/{case_id}/evidence", response_model=EvidenceOut)
def create_evidence(case_id: str, payload: EvidenceCreate, db: Session = Depends(get_db),
                     actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    item = EvidenceItem(
        case_id=case_id,
        document_id=payload.document_id,
        label=payload.label,
        source_text=payload.source_text,
        page_number=payload.page_number,
        section=payload.section,
        source_location_known=payload.page_number is not None or payload.section is not None,
        extraction_method=payload.extraction_method,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    log_audit_event(db, case_id, actor=actor.user_id, actor_type="USER", action="EVIDENCE_CREATED",
                     target_type="EVIDENCE", target_id=item.id)
    snapshot_evidence(db, item, reason="CREATED")
    db.commit()
    db.refresh(item)
    return item


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return db.query(EvidenceItem).filter(EvidenceItem.case_id == case_id).all()


@router.get("/evidence/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    item = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    require_case_with_access(db, item.case_id, actor)
    return item
