"""Structural materiality classifier for NYAYA-SATYA.

Classifies nodes by their structural importance in the case graph.
Materiality here is STRUCTURAL, not legal. Never says 'legally material'
unless a human/legal rule explicitly establishes that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.relationships import RelationshipType


class MaterialityLevel(str, Enum):
    STRUCTURALLY_MATERIAL = "STRUCTURALLY_MATERIAL"
    STRUCTURALLY_MINOR = "STRUCTURALLY_MINOR"
    STRUCTURALLY_IRRELEVANT = "STRUCTURALLY_IRRELEVANT"
    UNKNOWN = "UNKNOWN"


@dataclass
class MaterialityAssessment:
    """Assessment of a node's structural materiality."""

    node_id: str
    node_type: str
    level: MaterialityLevel
    dependent_claim_count: int = 0
    dependency_depth: int = 0
    issue_reach: int = 0
    contradiction_exposure: int = 0
    basis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "level": self.level.value,
            "dependent_claim_count": self.dependent_claim_count,
            "dependency_depth": self.dependency_depth,
            "issue_reach": self.issue_reach,
            "contradiction_exposure": self.contradiction_exposure,
            "basis": self.basis,
        }


class MaterialityClassifier:
    """Transparent structural materiality classifier."""

    def assess_evidence(self, evidence_id: str, twin: CaseDigitalTwin) -> MaterialityAssessment:
        """Assess structural materiality of an evidence item."""
        dep_claims = 0
        issue_reach = 0
        contradiction_exposure = 0
        basis: list[str] = []

        for claim in twin.claims.values():
            if evidence_id in claim.supporting_evidence_ids or evidence_id in claim.source_evidence_ids:
                dep_claims += 1
            if evidence_id in claim.contradicting_evidence_ids:
                contradiction_exposure += 1

        for issue in twin.issues.values():
            if evidence_id in issue.related_evidence_ids:
                issue_reach += 1

        # Compute depth via dependency chain
        dep_depth = self._compute_evidence_depth(evidence_id, twin)

        # Classify
        if dep_claims >= 3 or (dep_claims >= 2 and issue_reach >= 1):
            level = MaterialityLevel.STRUCTURALLY_MATERIAL
            basis.append(f"Supports {dep_claims} claims, reaches {issue_reach} issues")
        elif dep_claims >= 1:
            level = MaterialityLevel.STRUCTURALLY_MINOR
            basis.append(f"Supports {dep_claims} claim(s)")
        elif contradiction_exposure > 0:
            level = MaterialityLevel.STRUCTURALLY_MINOR
            basis.append(f"Involved in {contradiction_exposure} contradiction(s)")
        else:
            level = MaterialityLevel.STRUCTURALLY_IRRELEVANT
            basis.append("No dependent claims or issues found")

        return MaterialityAssessment(
            node_id=evidence_id,
            node_type="EVIDENCE",
            level=level,
            dependent_claim_count=dep_claims,
            dependency_depth=dep_depth,
            issue_reach=issue_reach,
            contradiction_exposure=contradiction_exposure,
            basis=basis,
        )

    def assess_claim(self, claim_id: str, twin: CaseDigitalTwin) -> MaterialityAssessment:
        """Assess structural materiality of a claim."""
        dep_count = 0
        issue_reach = 0
        basis: list[str] = []

        # Count claims that DEPEND_ON this claim
        for rel in twin.relationships.values():
            if rel.target_id == claim_id and rel.relationship_type == RelationshipType.DEPENDS_ON:
                dep_count += 1

        for issue in twin.issues.values():
            if claim_id in issue.related_claim_ids:
                issue_reach += 1

        dep_depth = self._compute_claim_depth(claim_id, twin)

        if dep_count >= 2 or (dep_count >= 1 and issue_reach >= 1):
            level = MaterialityLevel.STRUCTURALLY_MATERIAL
            basis.append(f"{dep_count} claims depend on this, reaches {issue_reach} issues")
        elif dep_count >= 1 or issue_reach >= 1:
            level = MaterialityLevel.STRUCTURALLY_MINOR
            basis.append(f"{dep_count} dependent claim(s), {issue_reach} issue(s)")
        else:
            level = MaterialityLevel.STRUCTURALLY_IRRELEVANT
            basis.append("No downstream dependencies or issue connections")

        return MaterialityAssessment(
            node_id=claim_id,
            node_type="CLAIM",
            level=level,
            dependent_claim_count=dep_count,
            dependency_depth=dep_depth,
            issue_reach=issue_reach,
            basis=basis,
        )

    def _compute_evidence_depth(self, evidence_id: str, twin: CaseDigitalTwin) -> int:
        """Compute max depth of dependent claims."""
        direct_claims = [
            cid for cid, c in twin.claims.items()
            if evidence_id in c.supporting_evidence_ids
        ]
        if not direct_claims:
            return 0
        max_depth = 0
        for cid in direct_claims:
            depth = self._compute_claim_depth(cid, twin)
            max_depth = max(max_depth, depth + 1)
        return max_depth

    def _compute_claim_depth(self, claim_id: str, twin: CaseDigitalTwin, visited: set[str] | None = None) -> int:
        """Compute dependency depth downstream from a claim."""
        if visited is None:
            visited = set()
        if claim_id in visited:
            return 0
        visited.add(claim_id)

        max_depth = 0
        for rel in twin.relationships.values():
            if rel.target_id == claim_id and rel.relationship_type == RelationshipType.DEPENDS_ON:
                depth = self._compute_claim_depth(rel.source_id, twin, visited) + 1
                max_depth = max(max_depth, depth)
        return max_depth
