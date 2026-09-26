"""Constraint contracts for NYAYA-SATYA Auto-Healer.

Defines architectural boundaries and validation rules for repair proposals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class ConstraintViolationError(ValueError):
    """Raised when a repair violates architectural safety constraints."""


@dataclass(frozen=True)
class RepairConstraints:
    """Configurable boundaries for repair candidate generation and execution."""

    min_evidence_support: float = 0.5
    min_legal_grounding: float = 0.4
    max_collateral_impact: float = 0.4
    max_actions_per_repair: int = 5
    allow_claim_removal: bool = True
    prohibit_new_unsupported_evidence: bool = True
    prohibit_unverified_authority_as_verified: bool = True
    prohibit_canonical_mutation: bool = True
    prohibited_terms: tuple[str, ...] = (
        "guilty",
        "innocent",
        "verdict",
        "win probability",
        "perjury detected",
        "fraud detected",
        "legally proven",
        "conviction likelihood",
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairConstraints:
        d = dict(data)
        if "prohibited_terms" in d:
            d["prohibited_terms"] = tuple(d["prohibited_terms"])
        return cls(**d)
