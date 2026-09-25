"""Missing-evidence contracts for NYAYA-SATYA.

Defines candidate missing evidence items that could resolve open questions or reduce uncertainty.
Strictly non-adjudicative: never claims that missing evidence actually exists in reality.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


@dataclass
class MissingEvidenceCandidate:
    """An evidentiary question where obtaining records could reduce uncertainty."""

    candidate_id: str
    case_id: str
    question: str
    related_claims: list[str] = field(default_factory=list)
    related_issue: str | None = None
    expected_evidence_type: str = "DOCUMENT"
    current_uncertainty: float = 0.8  # [0.0, 1.0]
    dependency: list[str] = field(default_factory=list)
    access_constraint: str = "NONE_NOTED"
    estimated_information_value: str = "HIGH"  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    provenance: list[ProvenanceRef] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.candidate_id.strip():
            raise ValueError("candidate_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not (0.0 <= self.current_uncertainty <= 1.0):
            raise ValueError(f"current_uncertainty must be in [0.0, 1.0], got {self.current_uncertainty}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["discovered_at"] = self.discovered_at.isoformat()
        data["provenance"] = [p.to_dict() for p in self.provenance]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissingEvidenceCandidate:
        d = dict(data)
        if isinstance(d.get("discovered_at"), str):
            d["discovered_at"] = datetime.fromisoformat(d["discovered_at"])
        if d.get("provenance"):
            d["provenance"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance"]
            ]
        return cls(**d)
