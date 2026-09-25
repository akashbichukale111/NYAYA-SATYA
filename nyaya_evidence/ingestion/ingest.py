"""Evidence Ingestion Service for NYAYA-SATYA.

Safe gateway for receiving evidence files.
Enforces size limits, extension whitelists, path traversal prevention,
SHA-256 fingerprinting, initial provenance tagging, and quarantine isolation.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from nyaya_evidence.contracts.evidence import (
    EvidenceArtifact,
    EvidenceItem,
    EvidenceSource,
    EvidenceStatus,
    MediaType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef

# Security boundaries
MAX_EVIDENCE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB ceiling
MIN_EVIDENCE_SIZE_BYTES = 1                  # Reject 0-byte files

# Extension whitelist to MediaType mapping
_EXTENSION_MEDIA_MAP: dict[str, MediaType] = {
    ".txt": MediaType.TEXT_PLAIN,
    ".pdf": MediaType.APPLICATION_PDF,
    ".docx": MediaType.APPLICATION_DOCX,
    ".json": MediaType.APPLICATION_JSON,
    ".csv": MediaType.TEXT_CSV,
}

# Dangerous executable extensions that must be rejected immediately
_DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".vbs", ".dll", ".scr", ".msi", ".com", ".ps1", ".py", ".bin"
}


class EvidenceIngestionError(ValueError):
    """Raised when evidence ingestion fails validation or security checks."""


def sanitize_filename(raw_filename: str) -> str:
    """Sanitizes filename against path traversal and dangerous characters."""
    if not raw_filename or not raw_filename.strip():
        raise EvidenceIngestionError("Filename cannot be empty")

    # Reject null bytes, path separators, or path traversal
    if "\0" in raw_filename or ".." in raw_filename or "/" in raw_filename or "\\" in raw_filename:
        raise EvidenceIngestionError(f"Path traversal or directory separators detected in filename: {raw_filename!r}")

    # Strip directory components (handles both / and \)
    basename = os.path.basename(raw_filename.replace("\\", "/"))

    # Whitelist characters: alphanumeric, dots, underscores, dashes, spaces
    cleaned = re.sub(r"[^\w\.\-\s]", "_", basename).strip()
    if not cleaned:
        raise EvidenceIngestionError("Filename is empty after sanitization")

    return cleaned


def detect_media_type(filename: str, raw_bytes: bytes) -> MediaType:
    """Detects and validates media type based on filename and magic bytes."""
    _, ext = os.path.splitext(filename.lower())
    if ext in _DANGEROUS_EXTENSIONS:
        raise EvidenceIngestionError(f"Executable/script file uploads are prohibited: {ext}")

    media_type = _EXTENSION_MEDIA_MAP.get(ext)
    if not media_type:
        raise EvidenceIngestionError(f"Unsupported file format: {ext!r}. Supported formats: {list(_EXTENSION_MEDIA_MAP.keys())}")

    # Magic byte verification
    if media_type is MediaType.APPLICATION_PDF:
        if not raw_bytes.startswith(b"%PDF-"):
            raise EvidenceIngestionError("File claims to be PDF but lacks %PDF- header")
    elif media_type is MediaType.APPLICATION_DOCX:
        if not raw_bytes.startswith(b"PK\x03\x04"):
            raise EvidenceIngestionError("File claims to be DOCX but lacks ZIP PK header")

    return media_type


def ingest_evidence(
    *,
    case_id: str,
    raw_bytes: bytes,
    filename: str,
    source_type: str = "DOCUMENT_UPLOAD",
    custodian: str = "UNKNOWN",
    chain_of_custody_notes: str = "",
    custom_metadata: dict[str, Any] | None = None,
) -> tuple[EvidenceItem, EvidenceArtifact, ProvenanceRef]:
    """Ingests raw evidence, computes SHA-256, assigns quarantine, and records provenance."""
    if not case_id or not case_id.strip():
        raise EvidenceIngestionError("case_id is required")

    size = len(raw_bytes)
    if size < MIN_EVIDENCE_SIZE_BYTES:
        raise EvidenceIngestionError(f"Uploaded evidence is empty ({size} bytes)")
    if size > MAX_EVIDENCE_SIZE_BYTES:
        raise EvidenceIngestionError(f"Uploaded evidence exceeds {MAX_EVIDENCE_SIZE_BYTES} bytes limit ({size} bytes)")

    clean_name = sanitize_filename(filename)
    media_type = detect_media_type(clean_name, raw_bytes)

    # Compute deterministic SHA-256
    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    evidence_id = f"ev_{uuid.uuid4().hex[:16]}"
    source_id = f"src_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)

    source = EvidenceSource(
        source_id=source_id,
        source_type=source_type,
        custodian=custodian,
        chain_of_custody_notes=chain_of_custody_notes,
        acquired_at=now,
    )

    # Provenance DNA: Source & Acquisition
    provenance = ProvenanceRef.create(
        source_id=source_id,
        source_type=source_type,
        evidence_id=evidence_id,
        content_hash=content_hash,
        extraction_metadata={
            "filename": clean_name,
            "media_type": media_type.value,
            "size_bytes": size,
            "stage": "INGESTION_QUARANTINED",
        },
    )

    # Strict isolation: always starts as QUARANTINED
    item = EvidenceItem(
        evidence_id=evidence_id,
        case_id=case_id.strip(),
        source_id=source_id,
        filename=clean_name,
        media_type=media_type,
        size_bytes=size,
        content_hash=content_hash,
        source=source,
        status=EvidenceStatus.QUARANTINED,
        acquisition_time=now,
        provenance_ref_id=provenance.ref_id,
        quarantine_reason="Awaiting security scanning and adversarial sanitization",
        metadata=custom_metadata or {},
    )

    artifact = EvidenceArtifact(
        evidence_id=evidence_id,
        content_hash=content_hash,
        raw_bytes=raw_bytes,
        media_type=media_type,
        created_at=now,
    )

    return item, artifact, provenance


__all__ = [
    "MAX_EVIDENCE_SIZE_BYTES",
    "EvidenceIngestionError",
    "detect_media_type",
    "ingest_evidence",
    "sanitize_filename",
]
