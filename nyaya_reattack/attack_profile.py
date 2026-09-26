"""Attack profile definitions for NYAYA-SATYA Independent Re-Attack Engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ReAttackStrategy(str, Enum):
    """Strategies employed by the independent re-attack engine."""

    TARGET_VERIFICATION_PROBE = "TARGET_VERIFICATION_PROBE"
    COLLATERAL_CONTRADICTION_SCAN = "COLLATERAL_CONTRADICTION_SCAN"
    UNSUPPORTED_ASSERTION_PROBE = "UNSUPPORTED_ASSERTION_PROBE"
    PROVENANCE_BREAK_SCAN = "PROVENANCE_BREAK_SCAN"
    AUTHORITY_VALIDITY_PROBE = "AUTHORITY_VALIDITY_PROBE"
    TIMELINE_INSTABILITY_PROBE = "TIMELINE_INSTABILITY_PROBE"
    CAUSAL_DEPENDENCY_STRESS = "CAUSAL_DEPENDENCY_STRESS"
    INJECTION_RESILIENCE_PROBE = "INJECTION_RESILIENCE_PROBE"
    SUBSTITUTION_ERROR_SCAN = "SUBSTITUTION_ERROR_SCAN"


@dataclass(frozen=True)
class AttackProfile:
    """Configuration profile governing the independent re-attack suite."""

    profile_id: str
    strategies: tuple[ReAttackStrategy, ...] = tuple(ReAttackStrategy)
    intensity: str = "COMPREHENSIVE"  # STANDARD, COMPREHENSIVE, STRESS
    max_probes_per_claim: int = 5
    allow_adversarial_hypotheses: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "strategies": [s.value for s in self.strategies],
            "intensity": self.intensity,
            "max_probes_per_claim": self.max_probes_per_claim,
            "allow_adversarial_hypotheses": self.allow_adversarial_hypotheses,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttackProfile:
        d = dict(data)
        if "strategies" in d:
            d["strategies"] = tuple(ReAttackStrategy(s) for s in d["strategies"])
        return cls(**d)
