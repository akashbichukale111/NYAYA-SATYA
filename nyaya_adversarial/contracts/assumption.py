"""Assumption contracts for NYAYA-SATYA Assumption Registry.

Represents explicit and structural assumptions underlying arguments, claims,
and evidence in the case.
Strictly non-adjudicative: never silently promotes assumptions into established facts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class AssumptionStatus(str, Enum):
    EXPLICIT = "EXPLICIT"
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTESTED = "CONTESTED"
    UNKNOWN = "UNKNOWN"


class AssumptionType(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    FACTUAL = "FACTUAL"
    EVIDENTIARY = "EVIDENTIARY"
    TEMPORAL = "TEMPORAL"
    PROCEDURAL = "PROCEDURAL"


@dataclass
class Assumption:
    """An assumption that carries or bridges legal or factual claims."""

    assumption_id: str
    case_id: str
    description: str
    assumption_type: AssumptionType = AssumptionType.STRUCTURAL
    related_claim_ids: list[str] = field(default_factory=list)
    related_evidence_ids: list[str] = field(default_factory=list)
    support_status: AssumptionStatus = AssumptionStatus.UNSUPPORTED
    uncertainty: float = 0.5  # [0.0, 1.0]
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.assumption_id or not self.assumption_id.strip():
            raise ValueError("assumption_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError(f"uncertainty must be between 0.0 and 1.0, got {self.uncertainty}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["assumption_type"] = self.assumption_type.value
        data["support_status"] = self.support_status.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Assumption:
        d = dict(data)
        if isinstance(d.get("assumption_type"), str):
            d["assumption_type"] = AssumptionType(d["assumption_type"])
        if isinstance(d.get("support_status"), str):
            d["support_status"] = AssumptionStatus(d["support_status"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if d.get("provenance_refs"):
            d["provenance_refs"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance_refs"]
            ]
        return cls(**d)


@dataclass
class AssumptionRegistry:
    """Registry maintaining active assumptions for a case."""

    case_id: str
    assumptions: dict[str, Assumption] = field(default_factory=dict)

    def register(self, assumption: Assumption) -> None:
        if assumption.case_id != self.case_id:
            raise ValueError(
                f"Cross-case assumption rejected: registry={self.case_id}, assumption={assumption.case_id}"
            )
        self.assumptions[assumption.assumption_id] = assumption

    def get(self, assumption_id: str) -> Assumption | None:
        return self.assumptions.get(assumption_id)

    def list_all(self) -> list[Assumption]:
        return list(self.assumptions.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "assumptions": {k: v.to_dict() for k, v in self.assumptions.items()},
            "total_count": len(self.assumptions),
        }
