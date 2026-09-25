"""Evidence Item contracts for NYAYA-SATYA.

Establishes strict trust boundaries:
Evidence starts as UNTRUSTED and enters QUARANTINED status immediately.
It cannot be used in TARKA-VYUH reasoning until it reaches REGISTERED.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EvidenceStatus(str, Enum):
    RECEIVED = "RECEIVED"
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    SANITIZED = "SANITIZED"
    REGISTERED = "REGISTERED"
    PARSED = "PARSED"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"
    MALICIOUS = "MALICIOUS"
    CORRUPTED = "CORRUPTED"
    SCAN_FAILED = "SCAN_FAILED"


class MediaType(str, Enum):
    TEXT_PLAIN = "text/plain"
    APPLICATION_PDF = "application/pdf"
    APPLICATION_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    APPLICATION_JSON = "application/json"
    TEXT_CSV = "text/csv"
    APPLICATION_OCTET_STREAM = "application/octet-stream"
    UNKNOWN = "unknown"


@dataclass
class EvidenceSource:
    """The origin / provenance context of evidence."""

    source_id: str
    source_type: str  # "DOCUMENT_UPLOAD", "WITNESS_STATEMENT", "COURT_FILING", "REGULATORY_RECORD"
    custodian: str = "UNKNOWN"
    jurisdiction: str | None = None
    chain_of_custody_notes: str = ""
    acquired_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_id.strip():
            raise ValueError("source_id cannot be blank")
        if not self.source_type or not self.source_type.strip():
            raise ValueError("source_type cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["acquired_at"] = self.acquired_at.isoformat()
        return data


@dataclass
class EvidenceItem:
    """The primary evidence entity in the NYAYA-SATYA registry."""

    evidence_id: str
    case_id: str
    source_id: str
    filename: str
    media_type: MediaType
    size_bytes: int
    content_hash: str  # SHA-256 of raw bytes
    source: EvidenceSource
    status: EvidenceStatus = EvidenceStatus.QUARANTINED
    acquisition_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    provenance_ref_id: str | None = None
    duplicate_of_id: str | None = None  # If duplicate content is detected
    quarantine_reason: str = "Default quarantine upon ingestion"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.evidence_id.strip():
            raise ValueError("evidence_id cannot be blank")
        if len(self.evidence_id) > 128:
            raise ValueError("evidence_id cannot exceed 128 characters")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.evidence_id):
            raise ValueError(f"Invalid evidence_id format: {self.evidence_id!r}")

        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")

        if not self.filename or not self.filename.strip():
            raise ValueError("filename cannot be blank")
        if len(self.filename) > 255:
            raise ValueError("filename cannot exceed 255 characters")

        # Security check: disallow path traversal sequences in filename
        if ".." in self.filename or "/" in self.filename or "\\" in self.filename or "\0" in self.filename:
            raise ValueError(f"Path traversal or invalid characters in filename: {self.filename!r}")

        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError(f"size_bytes must be non-negative integer, got {self.size_bytes}")

        # Content hash validation (64-char SHA-256)
        if not self.content_hash or len(self.content_hash) != 64 or not re.fullmatch(r"^[0-9a-fA-F]{64}$", self.content_hash):
            raise ValueError(f"Invalid content_hash format (must be 64-character hex SHA-256): {self.content_hash!r}")

        if not isinstance(self.status, EvidenceStatus):
            self.status = EvidenceStatus(self.status)
        if not isinstance(self.media_type, MediaType):
            self.media_type = MediaType(self.media_type)

    @property
    def is_safe_for_reasoning(self) -> bool:
        """Only REGISTERED evidence can be consumed by TARKA-VYUH."""
        return self.status in {EvidenceStatus.REGISTERED, EvidenceStatus.PARSED}

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["media_type"] = self.media_type.value
        data["source"] = self.source.to_dict()
        data["acquisition_time"] = self.acquisition_time.isoformat()
        data["is_safe_for_reasoning"] = self.is_safe_for_reasoning
        return data


@dataclass
class EvidenceArtifact:
    """The raw payload and storage pointer for an ingested artifact."""

    evidence_id: str
    content_hash: str
    raw_bytes: bytes
    media_type: MediaType
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.raw_bytes:
            raise ValueError("Artifact bytes cannot be empty")


__all__ = [
    "EvidenceArtifact",
    "EvidenceItem",
    "EvidenceSource",
    "EvidenceStatus",
    "MediaType",
]
