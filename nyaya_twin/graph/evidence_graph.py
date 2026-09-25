"""Evidence Graph for NYAYA-SATYA Case Digital Twin.

Bridges Evidence World to Legal Reasoning World.
Answers:
- What evidence supports this claim?
- What evidence contradicts this claim?
- What claims depend on this evidence?
- What claims have no evidence?
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_twin.contracts.claims import Claim
from nyaya_twin.contracts.relationships import CaseRelationship, RelationshipType


class EvidenceGraph:
    """Graph structure managing evidence-to-claim and evidence-to-event edges."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self._evidence_refs: dict[str, SafeEvidenceRef] = {}
        # claim_id -> set of evidence_ids by relationship type
        self._claim_evidence: dict[str, dict[RelationshipType, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        # evidence_id -> set of claim_ids by relationship type
        self._evidence_claims: dict[str, dict[RelationshipType, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._all_claim_ids: set[str] = set()

    def add_evidence_ref(self, ref: SafeEvidenceRef) -> None:
        if ref.case_id != self.case_id:
            raise ValueError(
                f"Cross-case contamination: evidence {ref.evidence_id} belongs to case {ref.case_id}, expected {self.case_id}"
            )
        self._evidence_refs[ref.evidence_id] = ref

    def register_claim(self, claim_id: str) -> None:
        self._all_claim_ids.add(claim_id)

    def add_relationship(self, rel: CaseRelationship) -> None:
        if rel.case_id != self.case_id:
            raise ValueError(
                f"Cross-case contamination: relationship {rel.relationship_id} belongs to case {rel.case_id}, expected {self.case_id}"
            )

        # source is evidence, target is claim
        ev_id = rel.source_id
        cl_id = rel.target_id
        rtype = rel.relationship_type

        self._claim_evidence[cl_id][rtype].add(ev_id)
        self._evidence_claims[ev_id][rtype].add(cl_id)
        self._all_claim_ids.add(cl_id)

    def get_supporting_evidence(self, claim_id: str) -> list[str]:
        """Returns evidence IDs that support the claim."""
        return sorted(self._claim_evidence[claim_id][RelationshipType.SUPPORTS])

    def get_contradicting_evidence(self, claim_id: str) -> list[str]:
        """Returns evidence IDs that contradict the claim."""
        return sorted(self._claim_evidence[claim_id][RelationshipType.CONTRADICTS])

    def get_mentioning_evidence(self, claim_id: str) -> list[str]:
        """Returns evidence IDs that mention the claim."""
        return sorted(self._claim_evidence[claim_id][RelationshipType.MENTIONS])

    def get_claims_supported_by(self, evidence_id: str) -> list[str]:
        """Returns claim IDs supported by this evidence."""
        return sorted(self._evidence_claims[evidence_id][RelationshipType.SUPPORTS])

    def get_claims_contradicted_by(self, evidence_id: str) -> list[str]:
        """Returns claim IDs contradicted by this evidence."""
        return sorted(self._evidence_claims[evidence_id][RelationshipType.CONTRADICTS])

    def get_all_linked_claims(self, evidence_id: str) -> list[str]:
        """Returns all claim IDs linked to this evidence regardless of relationship."""
        linked: set[str] = set()
        for rtype, cset in self._evidence_claims[evidence_id].items():
            linked.update(cset)
        return sorted(linked)

    def get_unsupported_claims(self) -> list[str]:
        """Returns all registered claims that have ZERO supporting evidence."""
        unsupported = []
        for claim_id in sorted(self._all_claim_ids):
            if not self._claim_evidence[claim_id][RelationshipType.SUPPORTS]:
                unsupported.append(claim_id)
        return unsupported

    def get_contradicted_claims(self) -> list[str]:
        """Returns all registered claims that have at least one contradicting evidence."""
        contradicted = []
        for claim_id in sorted(self._all_claim_ids):
            if self._claim_evidence[claim_id][RelationshipType.CONTRADICTS]:
                contradicted.append(claim_id)
        return contradicted
