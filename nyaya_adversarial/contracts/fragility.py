"""Fragility and Achilles-Heel contracts for NYAYA-SATYA Jenga Engine.

Provides structural stress metrics, single-source dependency identification,
and Achilles-heel vulnerability reports.
Strictly non-adjudicative: never outputs case outcome probabilities or win rates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class StructuralSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class StructuralFragilityScore:
    """Bounded, deterministic structural fragility score."""

    score: float  # [0.0, 1.0] where 1.0 is maximum structural fragility
    dependency_breadth: int
    dependency_depth: int
    single_source_reliance: bool
    contradiction_exposure: int
    provenance_gaps: int
    unsupported_downstream_claims: int
    explanation: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be between 0.0 and 1.0, got {self.score}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StructuralFragilityScore:
        return cls(**data)


@dataclass
class FragilityReport:
    """Structural report when a node is removed or challenged during Jenga simulation."""

    target_id: str
    target_type: str  # "EVIDENCE" | "CLAIM"
    direct_dependents: list[str]
    indirect_dependents: list[str]
    unsupported_claim_count: int
    unresolved_issue_count: int
    contradiction_count: int
    provenance_gaps: int
    single_source_dependencies: list[str]
    assumptions_exposed: list[str]
    structural_fragility: StructuralFragilityScore
    explanation: str
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    simulated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["structural_fragility"] = self.structural_fragility.to_dict()
        data["simulated_at"] = self.simulated_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FragilityReport:
        d = dict(data)
        if isinstance(d.get("structural_fragility"), dict):
            d["structural_fragility"] = StructuralFragilityScore.from_dict(d["structural_fragility"])
        if isinstance(d.get("simulated_at"), str):
            d["simulated_at"] = datetime.fromisoformat(d["simulated_at"])
        if d.get("provenance_refs"):
            d["provenance_refs"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance_refs"]
            ]
        return cls(**d)


@dataclass
class AchillesHeel:
    """Identifies an evidence or claim node with high centrality and fragile support."""

    achilles_id: str
    case_id: str
    target_node_id: str
    target_type: str  # "EVIDENCE" | "CLAIM"
    centrality_score: float  # [0.0, 1.0]
    fragility_score: float  # [0.0, 1.0]
    severity: StructuralSeverity
    reasons: list[str]
    dependent_claims: list[str]
    conflicting_evidence_ids: list[str]
    provenance_gaps: int
    explanation: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.achilles_id or not self.achilles_id.strip():
            raise ValueError("achilles_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["detected_at"] = self.detected_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AchillesHeel:
        d = dict(data)
        if isinstance(d.get("severity"), str):
            d["severity"] = StructuralSeverity(d["severity"])
        if isinstance(d.get("detected_at"), str):
            d["detected_at"] = datetime.fromisoformat(d["detected_at"])
        return cls(**d)
