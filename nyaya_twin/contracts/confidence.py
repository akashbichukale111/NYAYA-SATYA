"""Confidence contracts for NYAYA-SATYA Case Digital Twin.

Replaces arbitrary fake percentage probabilities with explainable, structured confidence levels.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ConfidenceAssessment:
    """An explainable confidence assessment grounded in evidence and contradiction counts."""

    level: ConfidenceLevel
    basis: tuple[str, ...]
    evidence_count: int = 0
    contradiction_count: int = 0
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        data["basis"] = list(self.basis)
        data["assessed_at"] = self.assessed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfidenceAssessment:
        d = dict(data)
        if isinstance(d.get("level"), str):
            d["level"] = ConfidenceLevel(d["level"])
        if isinstance(d.get("basis"), list):
            d["basis"] = tuple(d["basis"])
        if isinstance(d.get("assessed_at"), str):
            d["assessed_at"] = datetime.fromisoformat(d["assessed_at"])
        return cls(**d)


def assess_claim_confidence(
    *,
    supporting_count: int,
    contradicting_count: int,
    has_primary_evidence: bool = True,
    has_unbroken_provenance: bool = True,
) -> ConfidenceAssessment:
    """Determines explainable confidence based purely on factual grounding."""
    basis: list[str] = []

    if not has_unbroken_provenance:
        return ConfidenceAssessment(
            level=ConfidenceLevel.LOW,
            basis=("Incomplete or unverified provenance chain detected",),
            evidence_count=supporting_count,
            contradiction_count=contradicting_count,
        )

    if contradicting_count > 0:
        basis.append(f"Subject to {contradicting_count} active evidence contradiction(s)")
        if supporting_count == 0:
            return ConfidenceAssessment(
                level=ConfidenceLevel.LOW,
                basis=tuple(basis + ["No direct supporting evidence registered"]),
                evidence_count=supporting_count,
                contradiction_count=contradicting_count,
            )
        return ConfidenceAssessment(
            level=ConfidenceLevel.MEDIUM,
            basis=tuple(basis + [f"Supported by {supporting_count} evidence item(s) despite conflicts"]),
            evidence_count=supporting_count,
            contradiction_count=contradicting_count,
        )

    if supporting_count == 0:
        return ConfidenceAssessment(
            level=ConfidenceLevel.UNKNOWN,
            basis=("No registered evidence references linked to claim",),
            evidence_count=0,
            contradiction_count=0,
        )

    if supporting_count >= 2 and has_primary_evidence:
        basis.append(f"Corroborated by {supporting_count} independent evidence reference(s)")
        basis.append("Zero identified evidence contradictions")
        return ConfidenceAssessment(
            level=ConfidenceLevel.HIGH,
            basis=tuple(basis),
            evidence_count=supporting_count,
            contradiction_count=0,
        )

    basis.append(f"Supported by {supporting_count} evidence reference(s)")
    basis.append("Zero identified evidence contradictions")
    return ConfidenceAssessment(
        level=ConfidenceLevel.MEDIUM,
        basis=tuple(basis),
        evidence_count=supporting_count,
        contradiction_count=0,
    )
