"""Evidence path traversals for NYAYA-SATYA Case Digital Twin.

Answers:
1. What evidence supports this claim?
2. What evidence contradicts this claim?
3. What claims depend on this evidence?
4. What claims have no evidence?
"""

from __future__ import annotations

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.relationships import RelationshipType


def get_supporting_evidence_for_claim(twin: CaseDigitalTwin, claim_id: str) -> list[str]:
    """Returns evidence IDs that support the given claim."""
    res: set[str] = set()
    # Check direct relationships
    for rel in twin.relationships.values():
        if (
            rel.target_id == claim_id
            and rel.relationship_type is RelationshipType.SUPPORTS
            and rel.source_type == "EVIDENCE"
        ):
            res.add(rel.source_id)

    # Also check claim supporting_evidence_ids list
    if claim_id in twin.claims:
        res.update(twin.claims[claim_id].supporting_evidence_ids)

    return sorted(res)


def get_contradicting_evidence_for_claim(twin: CaseDigitalTwin, claim_id: str) -> list[str]:
    """Returns evidence IDs that contradict the given claim."""
    res: set[str] = set()
    for rel in twin.relationships.values():
        if (
            rel.target_id == claim_id
            and rel.relationship_type is RelationshipType.CONTRADICTS
            and rel.source_type == "EVIDENCE"
        ):
            res.add(rel.source_id)

    if claim_id in twin.claims:
        res.update(twin.claims[claim_id].contradicting_evidence_ids)

    return sorted(res)


def get_evidence_dependent_claims(twin: CaseDigitalTwin, evidence_id: str) -> list[str]:
    """Returns all claim IDs that reference or depend on the given evidence item."""
    res: set[str] = set()
    for rel in twin.relationships.values():
        if rel.source_id == evidence_id and rel.target_type == "CLAIM":
            res.add(rel.target_id)

    for claim in twin.claims.values():
        if (
            evidence_id in claim.source_evidence_ids
            or evidence_id in claim.supporting_evidence_ids
            or evidence_id in claim.contradicting_evidence_ids
        ):
            res.add(claim.claim_id)

    return sorted(res)


def get_unsupported_claims(twin: CaseDigitalTwin) -> list[str]:
    """Returns all claim IDs in the twin that have zero supporting evidence."""
    unsupported = []
    for claim_id in sorted(twin.claims.keys()):
        sup = get_supporting_evidence_for_claim(twin, claim_id)
        if not sup:
            unsupported.append(claim_id)
    return unsupported
