"""
Contradiction Agent.

For each claim with 2+ supporting evidence items, runs a heuristic
pairwise contradiction check (LLMProvider.detect_contradiction) and, on
a hit, FLAGS it: creates a CONTRADICTS relationship and a Conflict row,
both REQUIRES_HUMAN_REVIEW. Flagging a potential conflict is additive
(nothing existing is changed or hidden) so it's written directly;
resolving a conflict (deciding who's right) is a separate, explicit
Human Legal Gate action handled by review_service, never by this agent.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import EvidenceRelationship, EvidenceItem, Claim, Conflict
from app.models.enums import RelationshipType, VerificationStatus
from app.core.llm_provider import get_llm_provider
from app.services.review_service import log_audit_event


def detect_contradictions(db: Session, case_id: str, actor_id: str = "ContradictionAgent") -> Dict:
    provider = get_llm_provider()
    claims = db.query(Claim).filter(Claim.case_id == case_id).all()
    flagged: List[str] = []

    for claim in claims:
        support_edges = (
            db.query(EvidenceRelationship)
            .filter(
                EvidenceRelationship.case_id == case_id,
                EvidenceRelationship.target_type == "CLAIM",
                EvidenceRelationship.target_id == claim.id,
                EvidenceRelationship.source_type == "EVIDENCE",
                EvidenceRelationship.is_active == True,  # noqa: E712
            )
            .all()
        )
        evidence_items = [
            db.query(EvidenceItem).filter(EvidenceItem.id == e.source_id).first() for e in support_edges
        ]
        evidence_items = [e for e in evidence_items if e is not None]

        for i in range(len(evidence_items)):
            for j in range(i + 1, len(evidence_items)):
                a, b = evidence_items[i], evidence_items[j]
                result = provider.detect_contradiction(a.source_text, b.source_text)
                if not result["contradiction"]:
                    continue

                already_flagged = (
                    db.query(EvidenceRelationship)
                    .filter(
                        EvidenceRelationship.case_id == case_id,
                        EvidenceRelationship.relationship_type == RelationshipType.CONTRADICTS.value,
                        EvidenceRelationship.source_id.in_([a.id, b.id]),
                        EvidenceRelationship.target_id.in_([a.id, b.id]),
                    )
                    .first()
                )
                if already_flagged:
                    continue

                rel = EvidenceRelationship(
                    case_id=case_id, source_type="EVIDENCE", source_id=a.id,
                    target_type="EVIDENCE", target_id=b.id,
                    relationship_type=RelationshipType.CONTRADICTS.value,
                    explanation=result["explanation"],
                    verification_status=VerificationStatus.REQUIRES_HUMAN_REVIEW.value,
                )
                db.add(rel)

                conflict = Conflict(
                    case_id=case_id, node_a_type="EVIDENCE", node_a_id=a.id,
                    node_b_type="EVIDENCE", node_b_id=b.id,
                    description=result["explanation"],
                    status="REQUIRES_HUMAN_REVIEW",
                )
                db.add(conflict)
                db.flush()
                flagged.append(conflict.id)

    log_audit_event(
        db, case_id, actor="ContradictionAgent", actor_type="AGENT",
        action="CONTRADICTIONS_FLAGGED", target_type="CASE", target_id=case_id,
        detail={"conflict_ids": flagged},
    )
    db.commit()
    return {"ok": True, "conflict_ids": flagged}
