"""Hypothesis management contracts for Evidence Conflict Arena.

Enables representation of multiple alternative hypotheses for an evidentiary conflict.
Strictly non-adjudicative: never picks a winning hypothesis merely because it sounds plausible.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class HypothesisStatus(str, Enum):
    SUPPORTED_BY_EVIDENCE = "SUPPORTED_BY_EVIDENCE"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTESTED = "CONTESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class ConflictHypothesis:
    """An alternative factual explanation for an evidentiary conflict."""

    hypothesis_id: str
    conflict_id: str
    case_id: str
    description: str
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.UNRESOLVED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.hypothesis_id.strip():
            raise ValueError("hypothesis_id cannot be blank")
        if not self.conflict_id or not self.conflict_id.strip():
            raise ValueError("conflict_id cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConflictHypothesis:
        d = dict(data)
        if isinstance(d.get("status"), str):
            d["status"] = HypothesisStatus(d["status"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if d.get("provenance_refs"):
            d["provenance_refs"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance_refs"]
            ]
        return cls(**d)
