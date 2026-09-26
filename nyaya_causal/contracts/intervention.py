"""Intervention contracts for NYAYA-SATYA Counterfactual Lab.

Models controlled hypothetical changes applied to a Case Digital Twin.
Interventions never mutate the canonical twin.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class InterventionOperation(str, Enum):
    REMOVE = "REMOVE"
    DISABLE = "DISABLE"
    CHANGE_VALUE = "CHANGE_VALUE"
    CHANGE_TIME = "CHANGE_TIME"
    CHANGE_RELATIONSHIP = "CHANGE_RELATIONSHIP"
    MARK_UNKNOWN = "MARK_UNKNOWN"
    MARK_CONTESTED = "MARK_CONTESTED"


class InterventionTargetType(str, Enum):
    EVIDENCE = "EVIDENCE"
    EVENT = "EVENT"
    CLAIM = "CLAIM"
    ASSUMPTION = "ASSUMPTION"
    ENTITY = "ENTITY"
    RELATIONSHIP = "RELATIONSHIP"


@dataclass
class Intervention:
    """A controlled hypothetical change to the case state."""

    intervention_id: str
    case_id: str
    target_id: str
    target_type: InterventionTargetType
    operation: InterventionOperation
    original_state: dict[str, Any] = field(default_factory=dict)
    hypothetical_state: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    assumptions: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.intervention_id or not self.intervention_id.strip():
            raise ValueError("intervention_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("target_id cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.intervention_id):
            raise ValueError(f"Invalid intervention_id format: {self.intervention_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    @property
    def scenario_hash(self) -> str:
        """Deterministic hash of the intervention parameters."""
        payload = {
            "intervention_id": self.intervention_id,
            "case_id": self.case_id,
            "target_id": self.target_id,
            "target_type": self.target_type.value,
            "operation": self.operation.value,
            "hypothetical_state": self.hypothetical_state,
        }
        return compute_sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["target_type"] = self.target_type.value
        data["operation"] = self.operation.value
        data["created_at"] = self.created_at.isoformat()
        data["scenario_hash"] = self.scenario_hash
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data
