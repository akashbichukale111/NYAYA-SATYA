"""Value-of-Information (VoI) Foundation contracts for NYAYA-SATYA.

Defines structural information value metrics and Next-Best-Evidence recommendations.
Strictly non-adjudicative: never outputs win probabilities or monetary optimization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class InformationValueRating(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class InformationValueBreakdown:
    """Explainable structural breakdown of information value."""

    rating: InformationValueRating
    score: float  # [0.0, 1.0]
    uncertainty_reduction: float  # [0.0, 1.0]
    claims_affected_count: int
    issues_affected_count: int
    contradiction_resolution_potential: int
    dependency_centrality: float  # [0.0, 1.0]
    acquisition_cost: str = "LOW"  # "LOW" | "MEDIUM" | "HIGH"
    acquisition_difficulty: str = "EASY"  # "EASY" | "MODERATE" | "DIFFICULT" | "RESTRICTED"
    explanation: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be between 0.0 and 1.0, got {self.score}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rating"] = self.rating.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InformationValueBreakdown:
        d = dict(data)
        if isinstance(d.get("rating"), str):
            d["rating"] = InformationValueRating(d["rating"])
        return cls(**d)


@dataclass
class NextBestEvidence:
    """Ranked next-best-evidence candidate prioritizing uncertainty reduction."""

    candidate_id: str
    question_resolved: str
    affected_claims: list[str]
    affected_issues: list[str]
    expected_uncertainty_reduction: float
    dependency_coverage: list[str]
    acquisition_constraints: str
    confidence: float
    information_value: InformationValueBreakdown
    explanation: str
    priority_rank: int = 1

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["information_value"] = self.information_value.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NextBestEvidence:
        d = dict(data)
        if isinstance(d.get("information_value"), dict):
            d["information_value"] = InformationValueBreakdown.from_dict(d["information_value"])
        return cls(**d)
