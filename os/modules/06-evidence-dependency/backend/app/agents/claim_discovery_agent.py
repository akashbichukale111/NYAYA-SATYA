"""
Claim Discovery Agent.

Proposes candidate Claims grounded directly in extracted evidence text
(the claim text is the evidence's own text -- never invented content
beyond what the source says) and links each with a direct SUPPORTS
relationship back to its originating evidence. New, UNVERIFIED claims
are additive and non-destructive, so this agent writes directly; every
write is audited and the claim starts REQUIRES_HUMAN_REVIEW.
"""
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.orm import EvidenceItem, Claim, EvidenceRelationship
from app.models.enums import VerificationStatus, RelationshipType
from app.services.review_service import log_audit_event
from app.services.time_machine_service import snapshot_claim


def discover_claims(db: Session, case_id: str, evidence_ids: List[str],
                     actor_id: str = "ClaimDiscoveryAgent") -> Dict:
    created_claim_ids: List[str] = []
    for eid in evidence_ids:
        ev = db.query(EvidenceItem).filter(EvidenceItem.id == eid, EvidenceItem.case_id == case_id).first()
        if not ev:
            continue
        claim = Claim(
            case_id=case_id,
            text=ev.source_text,  # grounded verbatim in the evidence -- never fabricated
            source="EXTRACTED",
            verification_status=VerificationStatus.REQUIRES_HUMAN_REVIEW.value,
            review_state="PENDING_DISCOVERY_REVIEW",
        )
        db.add(claim)
        db.flush()
        snapshot_claim(db, claim, reason="AGENT_DISCOVERED")
        rel = EvidenceRelationship(
            case_id=case_id, source_type="EVIDENCE", source_id=ev.id,
            target_type="CLAIM", target_id=claim.id,
            relationship_type=RelationshipType.SUPPORTS.value,
            support_kind="DIRECT_SUPPORT",
            explanation="Claim discovered directly from this evidence item's own text.",
            verification_status=VerificationStatus.REQUIRES_HUMAN_REVIEW.value,
        )
        db.add(rel)
        created_claim_ids.append(claim.id)

    log_audit_event(
        db, case_id, actor="ClaimDiscoveryAgent", actor_type="AGENT",
        action="CLAIMS_DISCOVERED", target_type="CASE", target_id=case_id,
        detail={"claim_ids": created_claim_ids, "from_evidence_ids": evidence_ids},
    )
    db.commit()
    return {"ok": True, "claim_ids": created_claim_ids}
