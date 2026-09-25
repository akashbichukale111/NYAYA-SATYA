"""Case Digital Twin Root Contract for NYAYA-SATYA.

Unified representation of:
1. Physical / Factual World (Entities, Timeline Events)
2. Evidence World (SafeEvidenceRef, Provenance, Content Hashes)
3. Legal Reasoning World (Claims, Issues, Dependencies)

Supports deterministic serialization, integrity hashing, and version tracking.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_evidence.contradiction.engine import ContradictionCandidate
from nyaya_evidence.tarka_integration.safe_refs import SafeEvidenceRef
from nyaya_twin.contracts.claims import Claim
from nyaya_twin.contracts.entities import Entity
from nyaya_twin.contracts.events import TimelineEvent
from nyaya_twin.contracts.issues import Issue
from nyaya_twin.contracts.relationships import CaseRelationship
from tarka_vyuh.contracts.provenance import compute_sha256


@dataclass
class TwinVersionRecord:
    """Historical version tracking record for the Case Digital Twin."""

    version: int
    parent_version: int | None
    actor: str
    reason: str
    changed_nodes: list[str]
    changed_relationships: list[str]
    integrity_hash: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TwinVersionRecord:
        d = dict(data)
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


@dataclass
class CaseDigitalTwin:
    """Production-grade Case Digital Twin container."""

    twin_id: str
    case_id: str
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    entities: dict[str, Entity] = field(default_factory=dict)
    claims: dict[str, Claim] = field(default_factory=dict)
    issues: dict[str, Issue] = field(default_factory=dict)
    events: dict[str, TimelineEvent] = field(default_factory=dict)
    evidence_refs: dict[str, SafeEvidenceRef] = field(default_factory=dict)
    relationships: dict[str, CaseRelationship] = field(default_factory=dict)
    contradictions: list[ContradictionCandidate] = field(default_factory=list)
    temporal_conflicts: list[dict[str, Any]] = field(default_factory=list)
    unresolved_items: list[str] = field(default_factory=list)
    graph_integrity: dict[str, Any] = field(default_factory=dict)
    source_version: str = "3.0.0"
    version_history: list[TwinVersionRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.twin_id or not self.twin_id.strip():
            raise ValueError("twin_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.twin_id):
            raise ValueError(f"Invalid twin_id format: {self.twin_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    @property
    def integrity_hash(self) -> str:
        """Calculates deterministic integrity hash of the twin state."""
        return compute_twin_hash(self)

    def snapshot(self) -> dict[str, Any]:
        """Produces a deterministic, reproducible snapshot dict."""
        return {
            "twin_id": self.twin_id,
            "case_id": self.case_id,
            "version": self.version,
            "source_version": self.source_version,
            "integrity_hash": self.integrity_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "entities": {k: v.to_dict() for k, v in sorted(self.entities.items())},
            "claims": {k: v.to_dict() for k, v in sorted(self.claims.items())},
            "issues": {k: v.to_dict() for k, v in sorted(self.issues.items())},
            "events": {k: v.to_dict() for k, v in sorted(self.events.items())},
            "evidence_refs": {k: v.to_dict() for k, v in sorted(self.evidence_refs.items())},
            "relationships": {k: v.to_dict() for k, v in sorted(self.relationships.items())},
            "contradictions": [c.to_dict() for c in self.contradictions],
            "temporal_conflicts": self.temporal_conflicts,
            "unresolved_items": sorted(self.unresolved_items),
            "graph_integrity": self.graph_integrity,
            "version_history": [vh.to_dict() for vh in self.version_history],
        }

    def record_version(
        self,
        *,
        actor: str,
        reason: str,
        changed_nodes: list[str],
        changed_relationships: list[str],
    ) -> None:
        """Increments version and appends an immutable audit record."""
        current_hash = self.integrity_hash
        record = TwinVersionRecord(
            version=self.version,
            parent_version=self.version - 1 if self.version > 1 else None,
            actor=actor,
            reason=reason,
            changed_nodes=list(changed_nodes),
            changed_relationships=list(changed_relationships),
            integrity_hash=current_hash,
        )
        self.version_history.append(record)
        self.version += 1
        self.updated_at = datetime.now(UTC)


def compute_twin_hash(twin: CaseDigitalTwin) -> str:
    """Computes deterministic SHA-256 hash across sorted twin components."""
    data = {
        "twin_id": twin.twin_id,
        "case_id": twin.case_id,
        "version": twin.version,
        "entities": {k: v.canonical_label for k, v in sorted(twin.entities.items())},
        "claims": {k: (v.subject_entity_id, v.predicate, v.object_value, v.status.value) for k, v in sorted(twin.claims.items())},
        "issues": {k: (v.title, v.status.value) for k, v in sorted(twin.issues.items())},
        "events": {k: (v.title, v.event_time, v.time_precision.value) for k, v in sorted(twin.events.items())},
        "evidence_refs": {k: v.content_hash for k, v in sorted(twin.evidence_refs.items())},
        "relationships": {k: (v.source_id, v.target_id, v.relationship_type.value) for k, v in sorted(twin.relationships.items())},
    }
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
