"""Conflict contracts for NYAYA-SATYA Evidence Conflict Arena.

Defines structured conflict objects between pieces of evidence, claims,
temporal assertions, or assumptions.
Strictly non-adjudicative: does not declare perjury or fraud.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class ConflictType(str, Enum):
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    NUMERIC_CONFLICT = "NUMERIC_CONFLICT"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    LOCATION_CONFLICT = "LOCATION_CONFLICT"
    SEQUENCE_CONFLICT = "SEQUENCE_CONFLICT"
    DOCUMENT_CONFLICT = "DOCUMENT_CONFLICT"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    ASSUMPTION_CONFLICT = "ASSUMPTION_CONFLICT"
    POSSIBLE_CONTRADICTION = "POSSIBLE_CONTRADICTION"
    UNRESOLVED = "UNRESOLVED"


class ConflictSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class EvidenceConflict:
    """Represents a discrete evidentiary conflict identified in the case."""

    conflict_id: str
    case_id: str
    conflict_type: ConflictType
    subject: str
    evidence_a_id: str
    evidence_b_id: str
    claim_ids: list[str] = field(default_factory=list)
    description: str = ""
    supporting_text_refs: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    uncertainty: float = 0.5  # [0.0, 1.0] where 1.0 is totally unresolved/uncertain
    status: str = "OPEN_FOR_REVIEW"
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.conflict_id or not self.conflict_id.strip():
            raise ValueError("conflict_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError(f"uncertainty must be between 0.0 and 1.0, got {self.uncertainty}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["conflict_type"] = self.conflict_type.value
        data["severity"] = self.severity.value
        data["detected_at"] = self.detected_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceConflict:
        d = dict(data)
        if isinstance(d.get("conflict_type"), str):
            d["conflict_type"] = ConflictType(d["conflict_type"])
        if isinstance(d.get("severity"), str):
            d["severity"] = ConflictSeverity(d["severity"])
        if isinstance(d.get("detected_at"), str):
            d["detected_at"] = datetime.fromisoformat(d["detected_at"])
        if d.get("provenance_refs"):
            d["provenance_refs"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance_refs"]
            ]
        return cls(**d)


@dataclass
class ConflictSet:
    """A collection of structured conflicts discovered for a given case."""

    case_id: str
    conflicts: list[EvidenceConflict] = field(default_factory=list)
    total_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.total_count = len(self.conflicts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "total_count": len(self.conflicts),
            "generated_at": self.generated_at.isoformat(),
        }
