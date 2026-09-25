"""Ingestion package for NYAYA-SATYA Evidence Foundation."""

from nyaya_evidence.ingestion.ingest import (
    MAX_EVIDENCE_SIZE_BYTES,
    EvidenceIngestionError,
    detect_media_type,
    ingest_evidence,
    sanitize_filename,
)

__all__ = [
    "MAX_EVIDENCE_SIZE_BYTES",
    "EvidenceIngestionError",
    "detect_media_type",
    "ingest_evidence",
    "sanitize_filename",
]
