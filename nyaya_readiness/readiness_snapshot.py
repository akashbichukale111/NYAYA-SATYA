"""Case readiness snapshot model for NYAYA-SATYA.

Measures structural completeness, evidence coverage, and review readiness.
Strictly non-adjudicative: NO win probabilities or case strength percentages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CaseReadinessSnapshot:
    """A structural snapshot of case preparedness prior to or following repair."""

    case_id: str
    snapshot_id: str
    total_claims: int
    claims_with_evidence: int
    evidence_coverage_ratio: float  # [0.0, 1.0]
    unresolved_contradictions_count: int
    provenance_coverage_ratio: float  # [0.0, 1.0]
    authority_verification_ratio: float  # [0.0, 1.0]
    evidence_gaps_count: int
    causal_dependency_coverage_ratio: float  # [0.0, 1.0]
    unresolved_assumptions_count: int
    unsupported_assertions_count: int
    reattack_findings_count: int
    repair_immunity_status: str
    perturbation_stability_score: float  # [0.0, 1.0]
    human_review_obligations_count: int
    twin_integrity_hash: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "snapshot_id": self.snapshot_id,
            "total_claims": self.total_claims,
            "claims_with_evidence": self.claims_with_evidence,
            "evidence_coverage_ratio": self.evidence_coverage_ratio,
            "unresolved_contradictions_count": self.unresolved_contradictions_count,
            "provenance_coverage_ratio": self.provenance_coverage_ratio,
            "authority_verification_ratio": self.authority_verification_ratio,
            "evidence_gaps_count": self.evidence_gaps_count,
            "causal_dependency_coverage_ratio": self.causal_dependency_coverage_ratio,
            "unresolved_assumptions_count": self.unresolved_assumptions_count,
            "unsupported_assertions_count": self.unsupported_assertions_count,
            "reattack_findings_count": self.reattack_findings_count,
            "repair_immunity_status": self.repair_immunity_status,
            "perturbation_stability_score": self.perturbation_stability_score,
            "human_review_obligations_count": self.human_review_obligations_count,
            "twin_integrity_hash": self.twin_integrity_hash,
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaseReadinessSnapshot:
        d = dict(data)
        if isinstance(d.get("evaluated_at"), str):
            d["evaluated_at"] = datetime.fromisoformat(d["evaluated_at"])
        return cls(**d)
