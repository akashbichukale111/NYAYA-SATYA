"""Entity contracts for NYAYA-SATYA Case Digital Twin.

Models persons, organizations, assets, locations, and documents with explicit resolution states.
Never assumes two similar names belong to the same person without explicit corroboration.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from tarka_vyuh.contracts.provenance import ProvenanceRef


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    ASSET = "ASSET"
    DOCUMENT = "DOCUMENT"
    EVENT = "EVENT"
    OTHER = "OTHER"


class EntityStatus(str, Enum):
    VERIFIED_IDENTITY = "VERIFIED_IDENTITY"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    UNRESOLVED = "UNRESOLVED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EntityResolutionType(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    ALIAS_MATCH = "ALIAS_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class Entity:
    """A factual entity identified in the Case Digital Twin."""

    entity_id: str
    case_id: str
    entity_type: EntityType
    canonical_label: str
    aliases: list[str] = field(default_factory=list)
    source_evidence_ids: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: EntityStatus = EntityStatus.POSSIBLE_MATCH
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.canonical_label or not self.canonical_label.strip():
            raise ValueError("canonical_label cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.entity_id):
            raise ValueError(f"Invalid entity_id format: {self.entity_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    def matches_label(self, label: str) -> EntityResolutionType:
        """Determines label matching type deterministically."""
        clean = label.strip()
        if not clean:
            return EntityResolutionType.UNRESOLVED

        if clean.lower() == self.canonical_label.lower():
            return EntityResolutionType.EXACT_MATCH

        for alias in self.aliases:
            if clean.lower() == alias.lower():
                return EntityResolutionType.ALIAS_MATCH

        # Check for token overlap or prefix (possible match)
        clean_tokens = set(re.findall(r"\w+", clean.lower()))
        canon_tokens = set(re.findall(r"\w+", self.canonical_label.lower()))
        if clean_tokens and clean_tokens.issubset(canon_tokens):
            return EntityResolutionType.POSSIBLE_MATCH

        return EntityResolutionType.UNRESOLVED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entity_type"] = self.entity_type.value
        data["confidence"] = self.confidence.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entity:
        d = dict(data)
        if isinstance(d.get("entity_type"), str):
            d["entity_type"] = EntityType(d["entity_type"])
        if isinstance(d.get("confidence"), str):
            d["confidence"] = ConfidenceLevel(d["confidence"])
        if isinstance(d.get("status"), str):
            d["status"] = EntityStatus(d["status"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if isinstance(d.get("updated_at"), str):
            d["updated_at"] = datetime.fromisoformat(d["updated_at"])
        if "provenance_refs" in d:
            d["provenance_refs"] = [
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            ]
        return cls(**d)
