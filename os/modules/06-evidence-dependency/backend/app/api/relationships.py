from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import EvidenceRelationship
from app.schemas.schemas import RelationshipCreate, RelationshipOut
from app.services.review_service import log_audit_event

router = APIRouter()

VALID_NODE_TYPES = {"EVIDENCE", "CLAIM", "ISSUE"}


@router.post("/cases/{case_id}/relationships", response_model=RelationshipOut)
def create_relationship(case_id: str, payload: RelationshipCreate, db: Session = Depends(get_db),
                         actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)

    rel = EvidenceRelationship(
        case_id=case_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        relationship_type=payload.relationship_type,
        support_kind=payload.support_kind,
        explanation=payload.explanation,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    log_audit_event(db, case_id, actor=actor.user_id, actor_type="USER", action="RELATIONSHIP_CREATED",
                     target_type="RELATIONSHIP", target_id=rel.id)
    db.commit()
    return rel


@router.get("/cases/{case_id}/relationships", response_model=list[RelationshipOut])
def list_relationships(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return db.query(EvidenceRelationship).filter(EvidenceRelationship.case_id == case_id).all()
