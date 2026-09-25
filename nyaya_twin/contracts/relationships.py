"""Relationship contracts for NYAYA-SATYA Case Digital Twin.

Models typed directed edges across:
- Evidence -> Claim (SUPPORTS, CONTRADICTS, MENTIONS, DERIVED_FROM, etc.)
- Claim -> Claim (DEPENDS_ON, CORROBORATES, CHALLENGES)
- Claim -> Issue (SUBMITTED_UNDER, RELEVANT_TO)
- Entity -> Event / Claim (PARTICIPATES_IN, SUBJECT_OF)
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class RelationshipType(str, Enum):
    # Evidence -> Claim
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    MENTIONS = "MENTIONS"
    DERIVED_FROM = "DERIVED_FROM"
    QUALIFIES = "QUALIFIES"
    REFUTES = "REFUTES"
    TEMPORALLY_RELATES_TO = "TEMPORALLY_RELATES_TO"

    # Claim -> Claim
    DEPENDS_ON = "DEPENDS_ON"
    CORROBORATES = "CORROBORATES"
    CHALLENGES = "CHALLENGES"

    # Claim -> Issue
    SUBMITTED_UNDER = "SUBMITTED_UNDER"
    RELEVANT_TO = "RELEVANT_TO"

    # Entity -> Event / Claim
    PARTICIPATES_IN = "PARTICIPATES_IN"
    SUBJECT_OF = "SUBJECT_OF"


@dataclass(frozen=True)
class CaseRelationship:
    """A directed, typed, provenance-backed edge in the Case Digital Twin."""

    relationship_id: str
    case_id: str
    source_id: str
    source_type: str  # "EVIDENCE", "CLAIM", "ENTITY", "EVENT", "ISSUE"
    target_id: str
    target_type: str  # "CLAIM", "ISSUE", "EVENT", "ENTITY"
    relationship_type: RelationshipType
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance_refs: tuple[ProvenanceRef, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.relationship_id or not self.relationship_id.strip():
            raise ValueError("relationship_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.source_id or not self.source_id.strip():
            raise ValueError("source_id cannot be blank")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("target_id cannot be blank")
        if self.source_id == self.target_id and self.relationship_type is RelationshipType.DEPENDS_ON:
            raise ValueError(f"Self-dependency prohibited: node {self.source_id} cannot depend on itself")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.relationship_id):
            raise ValueError(f"Invalid relationship_id format: {self.relationship_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["relationship_type"] = self.relationship_type.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaseRelationship:
        d = dict(data)
        if isinstance(d.get("relationship_type"), str):
            d["relationship_type"] = RelationshipType(d["relationship_type"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if "provenance_refs" in d:
            d["provenance_refs"] = tuple(
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            )
        return cls(**d)
