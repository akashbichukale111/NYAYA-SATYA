"""Causal node contracts for NYAYA-SATYA Causal Reasoning Engine.

Represents typed nodes in the causal graph over the Case Digital Twin.
Nodes can represent events, facts, claims, evidence, assumptions, conditions,
issues, or procedural steps.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class CausalNodeType(str, Enum):
    EVENT = "EVENT"
    FACT = "FACT"
    CLAIM = "CLAIM"
    EVIDENCE = "EVIDENCE"
    ASSUMPTION = "ASSUMPTION"
    CONDITION = "CONDITION"
    ISSUE = "ISSUE"
    PROCEDURAL_STEP = "PROCEDURAL_STEP"


class CausalNodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    CONTESTED = "CONTESTED"
    UNKNOWN = "UNKNOWN"
    REMOVED = "REMOVED"


@dataclass
class CausalNode:
    """A typed node in the causal graph."""

    node_id: str
    case_id: str
    node_type: CausalNodeType
    label: str
    twin_reference_id: str = ""  # ID in the CaseDigitalTwin (claim_id, event_id, etc.)
    description: str = ""
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    status: CausalNodeStatus = CausalNodeStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise ValueError("node_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.label or not self.label.strip():
            raise ValueError("label cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.node_id):
            raise ValueError(f"Invalid node_id format: {self.node_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["node_type"] = self.node_type.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data
