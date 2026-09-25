"""Traversal and impact analysis layer for NYAYA-SATYA Case Digital Twin."""

from __future__ import annotations

from nyaya_twin.traversal.claim_dependencies import (
    get_claim_ancestors,
    get_claim_descendants,
    get_claim_prerequisites,
)
from nyaya_twin.traversal.downstream_impact import (
    DownstreamImpactReport,
    compute_evidence_invalidation_impact,
)
from nyaya_twin.traversal.evidence_paths import (
    get_contradicting_evidence_for_claim,
    get_evidence_dependent_claims,
    get_supporting_evidence_for_claim,
    get_unsupported_claims,
)

__all__ = [
    "DownstreamImpactReport",
    "compute_evidence_invalidation_impact",
    "get_claim_ancestors",
    "get_claim_descendants",
    "get_claim_prerequisites",
    "get_contradicting_evidence_for_claim",
    "get_evidence_dependent_claims",
    "get_supporting_evidence_for_claim",
    "get_unsupported_claims",
]
