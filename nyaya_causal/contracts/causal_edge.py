"""Causal edge contracts for NYAYA-SATYA Causal Reasoning Engine.

Directed typed edges in the causal graph.
Not every relationship is causal. SUPPORTS does NOT automatically mean CAUSES.
Causal edges require an explicit causal_basis.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from tarka_vyuh.contracts.provenance import ProvenanceRef


class CausalRelationshipType(str, Enum):
    CAUSES = "CAUSES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    DEPENDS_ON = "DEPENDS_ON"
    PRECONDITION_FOR = "PRECONDITION_FOR"
    ENABLES = "ENABLES"
    BLOCKS = "BLOCKS"
    TEMPORALLY_PRECEDES = "TEMPORALLY_PRECEDES"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"


class CausalEdgeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONTESTED = "CONTESTED"
    DISABLED = "DISABLED"
    CAUSALITY_UNRESOLVED = "CAUSALITY_UNRESOLVED"


@dataclass
class CausalEdge:
    """A directed, typed, causal edge in the causal graph."""

    edge_id: str
    case_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: CausalRelationshipType
    causal_basis: str  # Explicit basis for causal claim
    supporting_evidence_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    confidence_state: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    created_by: str = "SYSTEM"
    status: CausalEdgeStatus = CausalEdgeStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.edge_id or not self.edge_id.strip():
            raise ValueError("edge_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.source_node_id or not self.source_node_id.strip():
            raise ValueError("source_node_id cannot be blank")
        if not self.target_node_id or not self.target_node_id.strip():
            raise ValueError("target_node_id cannot be blank")
        if not self.causal_basis or not self.causal_basis.strip():
            raise ValueError("causal_basis cannot be blank: every causal edge requires an explicit basis")
        if self.source_node_id == self.target_node_id:
            raise ValueError(f"Self-referencing causal edge prohibited: {self.source_node_id}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.edge_id):
            raise ValueError(f"Invalid edge_id format: {self.edge_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    @property
    def is_causal(self) -> bool:
        """True if edge represents a causal or contributory relationship."""
        return self.relationship_type in (
            CausalRelationshipType.CAUSES,
            CausalRelationshipType.CONTRIBUTES_TO,
            CausalRelationshipType.ENABLES,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["relationship_type"] = self.relationship_type.value
        data["confidence_state"] = self.confidence_state.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data
