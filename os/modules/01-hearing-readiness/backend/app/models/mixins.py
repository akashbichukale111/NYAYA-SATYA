from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class ProvenanceMixin:
    """
    Every AI-derived or extracted record must be traceable.
    provenance_ref points to an AuditEvent / extraction record id.
    confidence is a calibrated 0..1 float, or null if not applicable.
    source is a free-text pointer to where this came from (document id, page, rule name).
    """
    provenance_ref = Column(String, nullable=True)
    confidence = Column(String, nullable=True)  # stored as HIGH/MEDIUM/LOW/UNKNOWN or "0.xx"
    source = Column(String, nullable=True)
