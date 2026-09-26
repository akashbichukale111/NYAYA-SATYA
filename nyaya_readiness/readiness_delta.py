"""Case Readiness Delta contract for NYAYA-SATYA.

Compares structural metrics before and after repair simulation.
Explicitly rejects outcome predictions and win probabilities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_readiness.readiness_snapshot import CaseReadinessSnapshot


@dataclass
class CaseReadinessDelta:
    """Quantitative structural delta between pre-repair and post-repair states."""

    case_id: str
    repair_id: str
    pre_snapshot: CaseReadinessSnapshot
    post_snapshot: CaseReadinessSnapshot
    evidence_coverage_delta: float
    contradictions_delta: int  # Negative is improvement (fewer contradictions)
    unsupported_claims_delta: int  # Negative is improvement
    unresolved_assumptions_delta: int
    provenance_coverage_delta: float
    authority_verification_delta: float
    regressions_count: int
    net_structural_progress: bool
    summary_of_changes: list[str] = field(default_factory=list)
    human_review_obligations: list[str] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "repair_id": self.repair_id,
            "pre_snapshot": self.pre_snapshot.to_dict(),
            "post_snapshot": self.post_snapshot.to_dict(),
            "evidence_coverage_delta": round(self.evidence_coverage_delta, 4),
            "contradictions_delta": self.contradictions_delta,
            "unsupported_claims_delta": self.unsupported_claims_delta,
            "unresolved_assumptions_delta": self.unresolved_assumptions_delta,
            "provenance_coverage_delta": round(self.provenance_coverage_delta, 4),
            "authority_verification_delta": round(self.authority_verification_delta, 4),
            "regressions_count": self.regressions_count,
            "net_structural_progress": self.net_structural_progress,
            "summary_of_changes": list(self.summary_of_changes),
            "human_review_obligations": list(self.human_review_obligations),
            "computed_at": self.computed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaseReadinessDelta:
        d = dict(data)
        if "pre_snapshot" in d:
            d["pre_snapshot"] = CaseReadinessSnapshot.from_dict(d["pre_snapshot"])
        if "post_snapshot" in d:
            d["post_snapshot"] = CaseReadinessSnapshot.from_dict(d["post_snapshot"])
        if isinstance(d.get("computed_at"), str):
            d["computed_at"] = datetime.fromisoformat(d["computed_at"])
        return cls(**d)
