"""
ORM models for the Evidence Dependency Engine domain.

Design notes:
- Every important entity has: id (uuid str), case_id, created_at,
  updated_at, status, and provenance where applicable (see PRODUCT spec).
- EvidenceRelationship is a single generic edge table (source/target are
  polymorphic via *_type + *_id) so the graph can hold Evidence->Evidence,
  Claim->Claim, Evidence->Claim, Claim->Issue, Evidence->Issue and
  Issue->Issue edges without N join tables.
- Historical/audit rows are never deleted (append-only) -- see
  AuditEvent and EvidenceVersion for the Time Machine.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Boolean, Integer, JSON
)
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.enums import (
    EvidenceState, VerificationStatus, UserRole, ReviewActionType,
    ReviewStatus, CrashTestEventType,
)


def gen_id() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.CITIZEN.value)
    created_at = Column(DateTime, default=now)


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    is_demo = Column(Boolean, default=False)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    evidence_items = relationship("EvidenceItem", back_populates="case", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="case", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    sha256_hash = Column(String, nullable=False)
    document_type = Column(String, default="UNKNOWN")  # PDF/DOCX/TXT/JSON/CSV
    extraction_method = Column(String, default="NONE")
    superseded_by_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    status = Column(String, default="INGESTED")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    case = relationship("Case", back_populates="documents")
    evidence_items = relationship("EvidenceItem", back_populates="document", cascade="all, delete-orphan")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True, index=True)
    label = Column(String, nullable=False)
    source_text = Column(Text, default="")

    # Provenance -- never fabricated. If unknown, fields stay None and the
    # API/UI must render "SOURCE_LOCATION_UNKNOWN".
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    source_location_known = Column(Boolean, default=False)
    extraction_method = Column(String, default="MANUAL_ENTRY")
    parent_evidence_id = Column(String, ForeignKey("evidence_items.id"), nullable=True)

    # Temporal
    event_date = Column(DateTime, nullable=True)
    discovery_date = Column(DateTime, nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    supersession_date = Column(DateTime, nullable=True)

    state = Column(String, default=EvidenceState.UNKNOWN.value)
    verification_status = Column(String, default=VerificationStatus.UNVERIFIED.value)
    superseded_by_evidence_id = Column(String, ForeignKey("evidence_items.id"), nullable=True)

    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    case = relationship("Case", back_populates="evidence_items")
    document = relationship("Document", back_populates="evidence_items")


class Claim(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    source = Column(String, default="USER_ENTERED")  # USER_ENTERED / EXTRACTED
    verification_status = Column(String, default=VerificationStatus.UNVERIFIED.value)
    temporal_validity = Column(String, nullable=True)
    superseded_by_claim_id = Column(String, ForeignKey("claims.id"), nullable=True)
    review_state = Column(String, default="NONE")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    case = relationship("Case", back_populates="claims")


class Issue(Base):
    __tablename__ = "issues"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    case = relationship("Case", back_populates="issues")


class EvidenceRelationship(Base):
    """Generic directed edge between any two graph nodes (Evidence/Claim/Issue)."""
    __tablename__ = "evidence_relationships"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)

    source_type = Column(String, nullable=False)  # EVIDENCE | CLAIM | ISSUE
    source_id = Column(String, nullable=False, index=True)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False, index=True)

    relationship_type = Column(String, nullable=False)
    support_kind = Column(String, nullable=True)  # DIRECT_SUPPORT / CORROBORATIVE_SUPPORT / ...
    confidence = Column(String, nullable=True)  # kept as string label, never a fabricated float
    explanation = Column(Text, default="")
    verification_status = Column(String, default=VerificationStatus.UNVERIFIED.value)
    provenance_note = Column(Text, default="")

    is_active = Column(Boolean, default=True)  # False when reversed/broken by crash test on real data
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Conflict(Base):
    __tablename__ = "conflicts"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    node_a_type = Column(String, nullable=False)
    node_a_id = Column(String, nullable=False)
    node_b_type = Column(String, nullable=False)
    node_b_id = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="REQUIRES_HUMAN_REVIEW")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    proposed_change = Column(JSON, default=dict)
    proposing_agent = Column(String, default="SYSTEM")
    status = Column(String, default=ReviewStatus.PENDING.value)
    decided_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    decision_note = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    decided_at = Column(DateTime, nullable=True)


class AuditEvent(Base):
    """Append-only audit log. Never updated or deleted."""
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    actor = Column(String, nullable=False)  # user id or agent name
    actor_type = Column(String, default="USER")  # USER | AGENT | SYSTEM
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    detail = Column(JSON, default=dict)
    created_at = Column(DateTime, default=now)


class EvidenceVersion(Base):
    """Append-only snapshot of an EvidenceItem's state, for the Time Machine."""
    __tablename__ = "evidence_versions"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    evidence_id = Column(String, ForeignKey("evidence_items.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    reason = Column(String, default="")
    created_at = Column(DateTime, default=now)


class ClaimVersion(Base):
    """Append-only snapshot of a Claim's state, for the Time Machine.
    Mirrors EvidenceVersion -- same pattern, same guarantees (never
    updated or deleted, written on every meaningful mutation)."""
    __tablename__ = "claim_versions"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    claim_id = Column(String, ForeignKey("claims.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)
    reason = Column(String, default="")
    created_at = Column(DateTime, default=now)


class CrashTestRun(Base):
    """A simulated (non-destructive) crash test result."""
    __tablename__ = "crash_test_runs"
    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    before_state = Column(JSON, default=dict)
    after_state = Column(JSON, default=dict)
    affected_claims = Column(JSON, default=list)
    affected_issues = Column(JSON, default=list)
    new_gaps = Column(JSON, default=list)
    new_conflicts = Column(JSON, default=list)
    criticality = Column(String, default="NONE")
    human_review_required = Column(Boolean, default=True)
    created_by = Column(String, default="SYSTEM")
    created_at = Column(DateTime, default=now)
