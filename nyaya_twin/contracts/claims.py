"""Claim contracts for NYAYA-SATYA Case Digital Twin.

Models structured claims made in the legal matter.
Evidence states are explicitly tracked (SUPPORTED, CONTRADICTED, UNSUPPORTED, etc.).
Strictly prohibits TRUE/FALSE judicial outcome labels.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from tarka_vyuh.contracts.provenance import ProvenanceRef


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"
    UNSUPPORTED = "UNSUPPORTED"
    PENDING_REVIEW = "PENDING_REVIEW"


class ClaimType(str, Enum):
    FACTUAL = "FACTUAL"
    LEGAL = "LEGAL"
    PROCEDURAL = "PROCEDURAL"
    DAMAGES = "DAMAGES"
    RELIEF = "RELIEF"
    OTHER = "OTHER"


@dataclass
class Claim:
    """A claim or factual proposition in the Case Digital Twin."""

    claim_id: str
    case_id: str
    subject_entity_id: str
    predicate: str
    object_value: str
    claim_type: ClaimType = ClaimType.FACTUAL
    source_evidence_ids: list[str] = field(default_factory=list)
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    status: ClaimStatus = ClaimStatus.PENDING_REVIEW
    created_from: str = "MANUAL_ENTRY"
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.claim_id or not self.claim_id.strip():
            raise ValueError("claim_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.subject_entity_id or not self.subject_entity_id.strip():
            raise ValueError("subject_entity_id cannot be blank")
        if not self.predicate or not self.predicate.strip():
            raise ValueError("predicate cannot be blank")
        if not self.object_value or not self.object_value.strip():
            raise ValueError("object_value cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.claim_id):
            raise ValueError(f"Invalid claim_id format: {self.claim_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    @property
    def statement(self) -> str:
        """Returns the natural declarative statement."""
        return f"{self.subject_entity_id} {self.predicate} {self.object_value}".strip()

    def evaluate_evidence_status(self) -> ClaimStatus:
        """Deterministically evaluates claim status from evidence connections."""
        if len(self.contradicting_evidence_ids) > 0:
            return ClaimStatus.CONTRADICTED
        if len(self.supporting_evidence_ids) == 0:
            return ClaimStatus.UNSUPPORTED
        if len(self.supporting_evidence_ids) == 1 and not self.source_evidence_ids:
            return ClaimStatus.PARTIALLY_SUPPORTED
        return ClaimStatus.SUPPORTED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["claim_type"] = self.claim_type.value
        data["confidence"] = self.confidence.value
        data["status"] = self.status.value
        data["statement"] = self.statement
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Claim:
        d = dict(data)
        d.pop("statement", None)
        if isinstance(d.get("claim_type"), str):
            d["claim_type"] = ClaimType(d["claim_type"])
        if isinstance(d.get("confidence"), str):
            d["confidence"] = ConfidenceLevel(d["confidence"])
        if isinstance(d.get("status"), str):
            d["status"] = ClaimStatus(d["status"])
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
