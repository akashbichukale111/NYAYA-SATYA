"""Provenance contracts for TARKA-VYUH.

Establishes first-class provenance tracking across the lifecycle:
SOURCE / EVIDENCE -> REASONING_PROPOSAL -> GOVERNANCE_DECISION -> HUMAN_DECISION -> EXECUTION_RECORD
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ProvenanceType(str, Enum):
    SOURCE = "SOURCE"
    EVIDENCE = "EVIDENCE"
    REASONING_PROPOSAL = "REASONING_PROPOSAL"
    GOVERNANCE_DECISION = "GOVERNANCE_DECISION"
    HUMAN_DECISION = "HUMAN_DECISION"
    EXECUTION_RECORD = "EXECUTION_RECORD"


def compute_sha256(content: str | bytes | dict[str, Any]) -> str:
    """Deterministic SHA-256 content hash."""
    if isinstance(content, dict):
        serialized = json.dumps(content, sort_keys=True, default=str)
        raw_bytes = serialized.encode("utf-8")
    elif isinstance(content, str):
        raw_bytes = content.encode("utf-8")
    else:
        raw_bytes = content
    return hashlib.sha256(raw_bytes).hexdigest()


@dataclass(frozen=True)
class ProvenanceRef:
    """A single verifiable provenance reference."""

    ref_id: str
    source_id: str
    source_type: str
    evidence_id: str
    content_hash: str
    extraction_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    parent_record_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        source_type: str,
        evidence_id: str,
        content: str | bytes | dict[str, Any] | None = None,
        content_hash: str | None = None,
        extraction_metadata: dict[str, Any] | None = None,
        parent_record_id: str | None = None,
    ) -> ProvenanceRef:
        if not source_id or not source_id.strip():
            raise ValueError("source_id cannot be empty")
        if not evidence_id or not evidence_id.strip():
            raise ValueError("evidence_id cannot be empty")
        if not source_type or not source_type.strip():
            raise ValueError("source_type cannot be empty")

        if content_hash is None:
            if content is None:
                raise ValueError("Either content or content_hash must be provided")
            computed_hash = compute_sha256(content)
        else:
            computed_hash = content_hash

        # Validate hash format (SHA-256 hex string)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", computed_hash):
            raise ValueError(f"Invalid content_hash format (must be 64-char hex SHA-256): {computed_hash}")

        ref_id = f"prov_{uuid.uuid4().hex[:16]}"
        return cls(
            ref_id=ref_id,
            source_id=source_id.strip(),
            source_type=source_type.strip(),
            evidence_id=evidence_id.strip(),
            content_hash=computed_hash.lower(),
            extraction_metadata=extraction_metadata or {},
            created_at=datetime.now(UTC),
            parent_record_id=parent_record_id,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


__all__ = [
    "ProvenanceRef",
    "ProvenanceType",
    "compute_sha256",
]
