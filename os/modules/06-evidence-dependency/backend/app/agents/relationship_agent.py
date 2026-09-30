"""
Relationship Agent.

Classifies existing SUPPORTS edges on a claim: the first evidence item
supporting a claim is DIRECT_SUPPORT; any additional evidence item that
supports the same claim from an independent document is upgraded to
CORROBORATIVE_SUPPORT (relationship_type CORROBORATES). This only
reclassifies edges that already exist (created by Claim Discovery or a
human) -- it never invents a new edge, and reclassification of existing,
already-created relationships is safe to apply directly since it doesn't
touch verification status or delete anything.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import EvidenceRelationship, EvidenceItem, Claim
from app.models.enums import RelationshipType, SupportKind
from app.services.review_service import log_audit_event


def classify_support(db: Session, case_id: str, actor_id: str = "RelationshipAgent") -> Dict:
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    upgraded: List[str] = []

    for claim in claims:
        support_edges = (
            db.query(EvidenceRelationship)
            .filter(
                EvidenceRelationship.case_id == case_id,
                EvidenceRelationship.target_type == "CLAIM",
                EvidenceRelationship.target_id == claim.id,
                EvidenceRelationship.source_type == "EVIDENCE",
                EvidenceRelationship.relationship_type.in_(
                    [RelationshipType.SUPPORTS.value, RelationshipType.CORROBORATES.value]
                ),
                EvidenceRelationship.is_active == True,  # noqa: E712
            )
            .order_by(EvidenceRelationship.created_at.asc())
            .all()
        )
        if len(support_edges) < 2:
            continue

        seen_documents = set()
        first_ev = db.query(EvidenceItem).filter(EvidenceItem.id == support_edges[0].source_id).first()
        if first_ev and first_ev.document_id:
            seen_documents.add(first_ev.document_id)

        for edge in support_edges[1:]:
            ev = db.query(EvidenceItem).filter(EvidenceItem.id == edge.source_id).first()
            if not ev:
                continue
            is_independent = ev.document_id is not None and ev.document_id not in seen_documents
            if ev.document_id:
                seen_documents.add(ev.document_id)
            if is_independent and edge.relationship_type != RelationshipType.CORROBORATES.value:
                edge.relationship_type = RelationshipType.CORROBORATES.value
                edge.support_kind = SupportKind.CORROBORATIVE_SUPPORT.value
                upgraded.append(edge.id)
            elif not is_independent and edge.support_kind != SupportKind.DUPLICATIVE_SUPPORT.value:
                edge.support_kind = SupportKind.DUPLICATIVE_SUPPORT.value

    log_audit_event(
        db, case_id, actor="RelationshipAgent", actor_type="AGENT",
        action="RELATIONSHIPS_CLASSIFIED", target_type="CASE", target_id=case_id,
        detail={"upgraded_to_corroborates": upgraded},
    )
    db.commit()
    return {"ok": True, "upgraded_relationship_ids": upgraded}
