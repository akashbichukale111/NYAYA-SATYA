"""
Secure ingestion pipeline (spec pipeline stages: SECURE INGESTION -> PARSING
-> DATE CANDIDATE DETECTION -> ... -> DEADLINE DIGITAL TWIN).

Section 1 scope: plain-text ingestion only (PDF/OCR ingestion is explicitly
out of scope until a later section — it is NOT faked here).
"""

import hashlib
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.db import Source, DateCandidate, Deadline, AuditLogEntry
from app.models.enums import SourceType, ProvenanceState, DeadlineStatus
from app.services.date_extraction import extract_date_candidates


MAX_INGEST_CHARS = 200_000  # basic guardrail against pathological input


class IngestionError(ValueError):
    pass


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _log(db: Session, entity_type: str, entity_id: str, action: str, detail: str = "") -> None:
    db.add(
        AuditLogEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor="system",
            detail=detail,
        )
    )


def ingest_text(db: Session, label: str, text: str, source_type: SourceType) -> Source:
    if not text or not text.strip():
        raise IngestionError("Refusing to ingest empty text.")
    if len(text) > MAX_INGEST_CHARS:
        raise IngestionError(f"Text exceeds ingestion limit of {MAX_INGEST_CHARS} characters.")

    checksum = _sha256(text)

    # Dedup: if we've already ingested byte-identical text, return the
    # existing Source rather than creating a duplicate twin.
    existing = db.query(Source).filter(Source.checksum == checksum).first()
    if existing:
        return existing

    source = Source(
        label=label,
        source_type=source_type,
        raw_text=text,
        checksum=checksum,
        ingested_at=datetime.utcnow(),
    )
    db.add(source)
    db.flush()  # populate source.id
    _log(db, "source", source.id, "ingested", f"label={label!r} chars={len(text)}")

    candidates = extract_date_candidates(text)
    for c in candidates:
        row = DateCandidate(
            source_id=source.id,
            raw_span=c.raw_span,
            context_snippet=c.context_snippet,
            resolved_date=c.resolved_date,
            is_relative=c.is_relative,
            relative_anchor_hint=c.relative_anchor_hint,
            provenance_state=c.provenance_state,
            confidence=c.confidence,
        )
        db.add(row)
        db.flush()
        _log(db, "date_candidate", row.id, "extracted",
             f"raw_span={c.raw_span!r} provenance={c.provenance_state.value}")

        # Every date candidate becomes a draft Deadline twin automatically —
        # nothing is silently hidden from the review queue, but nothing is
        # marked VERIFIED without a human either.
        deadline = Deadline(
            title=f"[{source_type.value}] {c.raw_span}",
            description=c.context_snippet,
            date_candidate_id=row.id,
            due_date=c.resolved_date,
            status=(
                DeadlineStatus.PENDING_REVIEW
                if c.provenance_state != ProvenanceState.REQUIRES_HUMAN_REVIEW
                else DeadlineStatus.PENDING_REVIEW
            ),
            provenance_state=c.provenance_state,
        )
        db.add(deadline)
        db.flush()
        _log(db, "deadline", deadline.id, "created",
             f"from date_candidate={row.id} provenance={c.provenance_state.value}")

    db.commit()
    db.refresh(source)
    return source
