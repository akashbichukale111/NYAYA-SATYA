"""Claim Graph for NYAYA-SATYA Case Digital Twin.

Models claim-to-claim dependencies (DEPENDS_ON, CORROBORATES, CHALLENGES)
and claim-to-issue relationships with cycle prevention.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from nyaya_twin.contracts.claims import Claim
from nyaya_twin.contracts.relationships import CaseRelationship, RelationshipType
from nyaya_twin.graph.dependency_graph import DependencyGraph


class ClaimGraph:
    """Graph structure managing claims and inter-claim dependencies."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self._claims: dict[str, Claim] = {}
        self._dependencies = DependencyGraph()
        self._corroborations: dict[str, set[str]] = defaultdict(set)
        self._challenges: dict[str, set[str]] = defaultdict(set)
        self._claim_to_issues: dict[str, set[str]] = defaultdict(set)

    def add_claim(self, claim: Claim) -> None:
        if claim.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: claim {claim.claim_id} belongs to {claim.case_id}, expected {self.case_id}")
        self._claims[claim.claim_id] = claim
        self._dependencies.add_node(claim.claim_id)

    def get_claim(self, claim_id: str) -> Claim | None:
        return self._claims.get(claim_id)

    def add_relationship(self, rel: CaseRelationship) -> None:
        if rel.case_id != self.case_id:
            raise ValueError(f"Cross-case contamination: relationship {rel.relationship_id} belongs to {rel.case_id}, expected {self.case_id}")

        if rel.relationship_type is RelationshipType.DEPENDS_ON:
            # source depends on target
            self._dependencies.add_dependency(rel.source_id, rel.target_id)
        elif rel.relationship_type is RelationshipType.CORROBORATES:
            self._corroborations[rel.source_id].add(rel.target_id)
            self._corroborations[rel.target_id].add(rel.source_id)
        elif rel.relationship_type is RelationshipType.CHALLENGES:
            self._challenges[rel.source_id].add(rel.target_id)
        elif rel.relationship_type in (RelationshipType.SUBMITTED_UNDER, RelationshipType.RELEVANT_TO):
            self._claim_to_issues[rel.source_id].add(rel.target_id)

    def get_prerequisites(self, claim_id: str) -> list[str]:
        """Returns direct prerequisite claims that claim_id depends on."""
        return self._dependencies.get_prerequisites(claim_id)

    def get_dependents(self, claim_id: str) -> list[str]:
        """Returns direct dependent claims that depend on claim_id."""
        return self._dependencies.get_dependents(claim_id)

    def get_ancestors(self, claim_id: str) -> list[str]:
        """Returns all upstream prerequisite claims."""
        return self._dependencies.get_ancestors(claim_id)

    def get_descendants(self, claim_id: str) -> list[str]:
        """Returns all downstream dependent claims."""
        return self._dependencies.get_descendants(claim_id)

    def get_corroborating_claims(self, claim_id: str) -> list[str]:
        return sorted(self._corroborations.get(claim_id, set()))

    def get_challenging_claims(self, claim_id: str) -> list[str]:
        return sorted(self._challenges.get(claim_id, set()))

    def get_issues_for_claim(self, claim_id: str) -> list[str]:
        return sorted(self._claim_to_issues.get(claim_id, set()))

    def topological_order(self) -> list[str]:
        """Returns claims in topological dependency order."""
        return self._dependencies.topological_sort()
