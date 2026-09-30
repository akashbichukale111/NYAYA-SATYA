"""
SQLAlchemy ORM models for Undertrial Liberty Sentinel.

Every table is strictly case-scoped via case_id (except User, Case itself,
and global audit/review tables which still carry case_id where relevant).
Strict case isolation is enforced at the query layer (see app/core/security.py)
in addition to these foreign keys.
"""
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, ProvenanceMixin, gen_id, utcnow


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: new_id("usr"))
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # UserRole
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=lambda: new_id("case"))
    case_reference = Column(String, nullable=False)
    title = Column(String, nullable=False)
    jurisdiction_note = Column(String, nullable=True)  # descriptive only, never used for legal rules
    is_demo = Column(Boolean, default=False)
    created_by_user_id = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")

    persons = relationship("Person", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    custody_events = relationship("CustodyEvent", back_populates="case", cascade="all, delete-orphan")


class Person(Base, TimestampMixin):
    __tablename__ = "persons"
    id = Column(String, primary_key=True, default=lambda: new_id("person"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False)
    role_in_case = Column(String, default="UNDERTRIAL")
    identifying_note = Column(String, nullable=True)

    case = relationship("Case", back_populates="persons")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: new_id("doc"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    safe_filename = Column(String, nullable=False)
    document_type = Column(String, default="OTHER")  # DocumentType
    mime_type = Column(String, nullable=False)
    size_bytes = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    status = Column(String, default="UPLOADED")  # DocumentStatus
    extraction_method = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    uploaded_by_user_id = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)

    case = relationship("Case", back_populates="documents")


class CustodyEvent(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "custody_events"
    id = Column(String, primary_key=True, default=lambda: new_id("cev"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    person_id = Column(String, ForeignKey("persons.id"), nullable=True)
    event_type = Column(String, nullable=False)  # CustodyEventType
    event_date = Column(String, nullable=True)   # ISO date string, may be null -> UNKNOWN_DATE
    date_type = Column(String, default="UNKNOWN_DATE")  # DateType
    verification_status = Column(String, default="UNVERIFIED")  # VerificationStatus
    notes = Column(String, nullable=True)

    case = relationship("Case", back_populates="custody_events")


class Hearing(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "hearings"
    id = Column(String, primary_key=True, default=lambda: new_id("hear"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    hearing_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    purpose = Column(String, nullable=True)
    status = Column(String, default="STATUS_UNKNOWN")  # HearingStatus
    result_summary = Column(String, nullable=True)  # verbatim-adjacent paraphrase of source, not a legal conclusion
    verification_status = Column(String, default="UNVERIFIED")


class Order(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=lambda: new_id("ord"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    related_hearing_id = Column(String, ForeignKey("hearings.id"), nullable=True)
    order_type_note = Column(String, nullable=True)  # free text description, e.g. "remand order"
    status = Column(String, default="ORDER_UNKNOWN_STATUS")  # OrderStatus
    mentioned_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    summary = Column(String, nullable=True)
    verification_status = Column(String, default="UNVERIFIED")
    superseded_by_order_id = Column(String, nullable=True)


class BailEvent(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "bail_events"
    id = Column(String, primary_key=True, default=lambda: new_id("bail"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # BailEventType
    event_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    related_hearing_id = Column(String, ForeignKey("hearings.id"), nullable=True)
    summary = Column(String, nullable=True)
    verification_status = Column(String, default="UNVERIFIED")


class ReleaseRelatedEvent(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "release_events"
    id = Column(String, primary_key=True, default=lambda: new_id("rel"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # ReleaseEventType
    event_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    current_status_confidence = Column(String, default="CURRENT_STATUS_UNKNOWN")  # CurrentStatusConfidence
    summary = Column(String, nullable=True)
    verification_status = Column(String, default="UNVERIFIED")


class FilingEvent(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "filing_events"
    id = Column(String, primary_key=True, default=lambda: new_id("file"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_type = Column(String, nullable=True)
    filing_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    summary = Column(String, nullable=True)


class LegalAidEvent(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "legal_aid_events"
    id = Column(String, primary_key=True, default=lambda: new_id("laid"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    event_note = Column(String, nullable=True)
    event_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")


class ProceduralEvent(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "procedural_events"
    id = Column(String, primary_key=True, default=lambda: new_id("proc"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # ProceduralEventType
    event_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    summary = Column(String, nullable=True)


class EvidenceItem(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "evidence_items"
    id = Column(String, primary_key=True, default=lambda: new_id("evid"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    description = Column(String, nullable=True)
    related_document_id = Column(String, nullable=True)


class DeadlineRecord(Base, TimestampMixin, ProvenanceMixin):
    """
    Tracks a SOURCE-STATED date only. This table must never contain a
    system-invented statutory deadline. date_type must be SOURCE_EXPLICIT_DATE,
    SOURCE_RELATIVE_DATE, or USER_ENTERED_DATE to be populated with a date;
    otherwise date_type=UNKNOWN_DATE and tracked_date is null.
    """
    __tablename__ = "deadline_records"
    id = Column(String, primary_key=True, default=lambda: new_id("dead"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    label = Column(String, nullable=False)
    tracked_date = Column(String, nullable=True)
    date_type = Column(String, default="UNKNOWN_DATE")
    related_entity_type = Column(String, nullable=True)
    related_entity_id = Column(String, nullable=True)


class Dependency(Base, TimestampMixin, ProvenanceMixin):
    __tablename__ = "dependencies"
    id = Column(String, primary_key=True, default=lambda: new_id("dep"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    dependency_type = Column(String, nullable=False)  # DependencyType
    from_entity_type = Column(String, nullable=False)
    from_entity_id = Column(String, nullable=False)
    to_entity_type = Column(String, nullable=False)
    to_entity_id = Column(String, nullable=False)
    status = Column(String, default="UNKNOWN")  # DependencyStatus


class AttentionItem(Base, TimestampMixin):
    __tablename__ = "attention_items"
    id = Column(String, primary_key=True, default=lambda: new_id("att"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    category = Column(String, nullable=False)  # AttentionCategory
    severity = Column(String, nullable=False)  # SignalSeverity
    reason = Column(String, nullable=False)
    source_refs = Column(JSON, default=list)
    status = Column(String, default="OPEN")  # SignalStatus
    requires_human_review = Column(Boolean, default=False)
    related_entity_type = Column(String, nullable=True)
    related_entity_id = Column(String, nullable=True)


class Conflict(Base, TimestampMixin):
    __tablename__ = "conflicts"
    id = Column(String, primary_key=True, default=lambda: new_id("conf"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    source_a_ref = Column(JSON, nullable=False)
    source_b_ref = Column(JSON, nullable=False)
    value_a = Column(String, nullable=False)
    value_b = Column(String, nullable=False)
    status = Column(String, default="OPEN")  # ConflictStatus
    resolved_value = Column(String, nullable=True)
    resolved_by_user_id = Column(String, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Verification(Base, TimestampMixin):
    __tablename__ = "verifications"
    id = Column(String, primary_key=True, default=lambda: new_id("ver"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    verification_status = Column(String, nullable=False)  # VerificationStatus
    verified_by_user_id = Column(String, nullable=True)
    note = Column(String, nullable=True)


class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_tasks"
    id = Column(String, primary_key=True, default=lambda: new_id("rev"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    task_type = Column(String, nullable=False)  # ReviewTaskType
    description = Column(String, nullable=False)
    related_entity_type = Column(String, nullable=True)
    related_entity_id = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # ReviewTaskStatus
    proposed_change = Column(JSON, nullable=True)
    decided_by_user_id = Column(String, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(String, nullable=True)


class CaseSnapshot(Base, TimestampMixin):
    """Immutable point-in-time snapshot of a case's derived state, for the Time Machine."""
    __tablename__ = "case_snapshots"
    id = Column(String, primary_key=True, default=lambda: new_id("snap"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    snapshot_reason = Column(String, nullable=False)  # e.g. "document_ingested", "manual", "crash_test"
    snapshot_data = Column(JSON, nullable=False)  # serialized digital twin at this point in time
    triggered_by_user_id = Column(String, nullable=True)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=lambda: new_id("aud"))
    case_id = Column(String, nullable=True, index=True)
    actor_user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)  # AuditAction
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, default=dict)


class ProvenanceRecord(Base, TimestampMixin):
    """Standalone provenance ledger entry, used when an entity's provenance needs independent audit history."""
    __tablename__ = "provenance_records"
    id = Column(String, primary_key=True, default=lambda: new_id("prov"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    source_document_id = Column(String, nullable=True)
    source_page = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
    source_text_snippet = Column(String, nullable=True)
    extraction_method = Column(String, nullable=True)
    content_hash = Column(String, nullable=True)
