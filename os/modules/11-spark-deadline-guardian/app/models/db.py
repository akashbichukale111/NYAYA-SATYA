"""
Persistence layer.

Everything here maps directly onto the pipeline in the spec:

    SOURCE -> DATE CANDIDATE -> DEADLINE (digital twin) -> DEPENDENCY EDGE
    -> CONFLICT -> AUDIT LOG

SQLite is used for Section 1 so the project runs with zero external
services. Swapping the engine URL in app/database.py to Postgres later
requires no model changes because everything goes through SQLAlchemy.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Float, Boolean, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import (
    SourceType, ProvenanceState, DeadlineStatus, ConflictType
)


def _uuid() -> str:
    return str(uuid.uuid4())


class Source(Base):
    """A document or event that dates were extracted from."""

    __tablename__ = "sources"

    id = Column(String, primary_key=True, default=_uuid)
    label = Column(String, nullable=False)
    source_type = Column(SAEnum(SourceType), nullable=False)
    raw_text = Column(Text, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    checksum = Column(String, nullable=False)  # sha256 of raw_text, for dedup/audit

    date_candidates = relationship("DateCandidate", back_populates="source")


class DateCandidate(Base):
    """A single date-like span found inside a Source, before it becomes a Deadline."""

    __tablename__ = "date_candidates"

    id = Column(String, primary_key=True, default=_uuid)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False)

    raw_span = Column(String, nullable=False)          # exact text matched, e.g. "within 30 days"
    context_snippet = Column(Text, nullable=False)     # surrounding text for human review
    resolved_date = Column(DateTime, nullable=True)     # null if relative/unresolved
    is_relative = Column(Boolean, default=False)
    relative_anchor_hint = Column(String, nullable=True)  # e.g. "service of notice"
    provenance_state = Column(SAEnum(ProvenanceState), nullable=False)
    confidence = Column(Float, nullable=False)          # 0..1, heuristic-based, never fabricated as certainty
    extracted_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="date_candidates")


class Deadline(Base):
    """The 'deadline digital twin' — the durable, trackable object."""

    __tablename__ = "deadlines"

    id = Column(String, primary_key=True, default=_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date_candidate_id = Column(String, ForeignKey("date_candidates.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(SAEnum(DeadlineStatus), default=DeadlineStatus.DRAFT)
    provenance_state = Column(SAEnum(ProvenanceState), nullable=False)
    superseded_by_id = Column(String, ForeignKey("deadlines.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by = Column(String, nullable=True)   # human identifier; null = not yet reviewed
    reviewed_at = Column(DateTime, nullable=True)


class DependencyEdge(Base):
    """Directed edge: `deadline_id` depends on `depends_on_id`."""

    __tablename__ = "dependency_edges"

    id = Column(String, primary_key=True, default=_uuid)
    deadline_id = Column(String, ForeignKey("deadlines.id"), nullable=False)
    depends_on_id = Column(String, ForeignKey("deadlines.id"), nullable=False)
    relationship_note = Column(String, nullable=True)  # e.g. "starts 30 days after"


class Conflict(Base):
    """A detected disagreement between dates/sources that needs human attention."""

    __tablename__ = "conflicts"

    id = Column(String, primary_key=True, default=_uuid)
    conflict_type = Column(SAEnum(ConflictType), nullable=False)
    deadline_a_id = Column(String, ForeignKey("deadlines.id"), nullable=False)
    deadline_b_id = Column(String, ForeignKey("deadlines.id"), nullable=True)
    detail = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolution_note = Column(Text, nullable=True)


class AuditLogEntry(Base):
    """Append-only trail. Every state transition in the pipeline writes one of these."""

    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=_uuid)
    entity_type = Column(String, nullable=False)   # "source" | "date_candidate" | "deadline" | "conflict"
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)         # "ingested" | "classified" | "reviewed" | ...
    actor = Column(String, nullable=False)          # "system" or a human identifier
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
