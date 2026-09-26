"""Repair Utility Vector (RUV) contracts for NYAYA-SATYA Auto-Healer.

Evaluates multi-dimensional utility of repair candidates.
Never collapses utility into a deceptive single 'legal score'.
Enforces strict hard constraints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RepairUtilityVector:
    """Multi-dimensional utility vector for an evaluated repair candidate.

    Never reduces to a single 'win probability' or 'legal score'.
    """

    evidence_support: float  # [0.0, 1.0] - degree of traceable evidence backing
    legal_grounding: float  # [0.0, 1.0] - verified authority coverage
    fragility_reduction: float  # [0.0, 1.0] - reduction in structural fragility
    collateral_impact: float  # [0.0, 1.0] - adverse unintended downstream shifts (0 = none)
    uncertainty: float  # [0.0, 1.0] - residual epistemic uncertainty
    new_vulnerabilities: int  # Must be 0 for acceptable repair
    critical_collateral_impact: int  # Must be 0 for acceptable repair
    unsupported_assertions_introduced: int = 0  # Must be 0
    fabricated_authorities_detected: int = 0  # Must be 0
    silent_fact_alterations: int = 0  # Must be 0
    canonical_twin_mutated: bool = False  # Must be False

    def __post_init__(self) -> None:
        for name, val in [
            ("evidence_support", self.evidence_support),
            ("legal_grounding", self.legal_grounding),
            ("fragility_reduction", self.fragility_reduction),
            ("collateral_impact", self.collateral_impact),
            ("uncertainty", self.uncertainty),
        ]:
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0], got {val}")

    @property
    def satisfies_hard_constraints(self) -> bool:
        """Check all non-negotiable architectural hard constraints."""
        return (
            self.new_vulnerabilities == 0
            and self.critical_collateral_impact == 0
            and self.unsupported_assertions_introduced == 0
            and self.fabricated_authorities_detected == 0
            and self.silent_fact_alterations == 0
            and not self.canonical_twin_mutated
        )

    def is_acceptable(
        self,
        *,
        min_evidence_support: float = 0.5,
        min_legal_grounding: float = 0.4,
        max_collateral_impact: float = 0.4,
    ) -> bool:
        """Evaluate if the utility vector qualifies the repair as acceptable."""
        if not self.satisfies_hard_constraints:
            return False
        return (
            self.evidence_support >= min_evidence_support
            and self.legal_grounding >= min_legal_grounding
            and self.collateral_impact <= max_collateral_impact
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["satisfies_hard_constraints"] = self.satisfies_hard_constraints
        data["is_acceptable"] = self.is_acceptable()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairUtilityVector:
        d = dict(data)
        d.pop("satisfies_hard_constraints", None)
        d.pop("is_acceptable", None)
        return cls(**d)
