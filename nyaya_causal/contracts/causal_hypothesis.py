"""Causal hypothesis contracts for NYAYA-SATYA.

Represents competing causal explanations.
The system preserves competing hypotheses and never selects one
merely because it has more text or more nodes.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from tarka_vyuh.contracts.provenance import ProvenanceRef


class CausalHypothesisStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTESTED = "CONTESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class CausalHypothesis:
    """A causal hypothesis linking cause nodes to effect nodes."""

    hypothesis_id: str
    case_id: str
    description: str
    cause_nodes: list[str]
    effect_nodes: list[str]
    intermediate_nodes: list[str] = field(default_factory=list)
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    confidence_state: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    status: CausalHypothesisStatus = CausalHypothesisStatus.UNRESOLVED
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.hypothesis_id.strip():
            raise ValueError("hypothesis_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.description or not self.description.strip():
            raise ValueError("description cannot be blank")
        if not self.cause_nodes:
            raise ValueError("cause_nodes must not be empty")
        if not self.effect_nodes:
            raise ValueError("effect_nodes must not be empty")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.hypothesis_id):
            raise ValueError(f"Invalid hypothesis_id format: {self.hypothesis_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence_state"] = self.confidence_state.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data
