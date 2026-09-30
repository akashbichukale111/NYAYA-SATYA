"""
Domain models — see docs/DOMAIN_MODEL.md for the full section-71 mapping.

NOT IMPLEMENTED in this build (tracked honestly rather than faked):
  Person/Party as a separate table (parties are stored as free-text on Case
  for demo purposes), Simulation persistence (simulations are computed
  on-the-fly, not stored), PrivacyPolicy as a configurable rule engine
  (rules are a static table in privacy/rules.py, not admin-editable yet).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum as SAEnum, Boolean, Integer, JSON
)
from sqlalchemy.orm import relationship

from database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class FactStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    DOCUMENT_SUPPORTED = "DOCUMENT_SUPPORTED"
    USER_REPORTED = "USER_REPORTED"
    INFERRED = "INFERRED"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"
    NOT_PROVIDED = "NOT_PROVIDED"
    SUPERSEDED = "SUPERSEDED"


class Sensitivity(str, enum.Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    HIGHLY_SENSITIVE = "HIGHLY_SENSITIVE"


class Role(str, enum.Enum):
    CITIZEN = "CITIZEN"
    PARALEGAL = "PARALEGAL"
    LEGAL_AID_WORKER = "LEGAL_AID_WORKER"
    ADVOCATE = "ADVOCATE"
    ADMINISTRATOR = "ADMINISTRATOR"
    REVIEWER = "REVIEWER"


class HandoffState(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"
    APPROVED = "APPROVED"
    TRANSFERRED = "TRANSFERRED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
    RETURNED_FOR_CORRECTION = "RETURNED_FOR_CORRECTION"
    VERIFIED = "VERIFIED"


class ConflictType(str, enum.Enum):
    DATE_CONFLICT = "DATE_CONFLICT"
    PARTY_CONFLICT = "PARTY_CONFLICT"
    EVENT_CONFLICT = "EVENT_CONFLICT"
    DOCUMENT_CONFLICT = "DOCUMENT_CONFLICT"
    AMOUNT_CONFLICT = "AMOUNT_CONFLICT"
    STATUS_CONFLICT = "STATUS_CONFLICT"
    LOCATION_CONFLICT = "LOCATION_CONFLICT"


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=lambda: gen_id("case"))
    title = Column(String, nullable=False)
    citizen_name = Column(String, nullable=True)
    preferred_language = Column(String, default="en")
    requested_help = Column(Text, nullable=True)
    citizen_narrative = Column(Text, nullable=True)  # raw free-form intake text
    parties = Column(JSON, default=list)  # [{name, role}]
    created_at = Column(DateTime, default=datetime.utcnow)
    is_demo = Column(Boolean, default=False)
    demo_tag = Column(String, nullable=True)  # e.g. "CASE_A"

    facts = relationship("Fact", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="case", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="case", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="case", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="case", cascade="all, delete-orphan")
    handoffs = relationship("Handoff", back_populates="case", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: gen_id("doc"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    filename = Column(String, nullable=False)
    safe_filename = Column(String, nullable=False)
    source_type = Column(String, default="upload")  # upload | ocr | manual
    extraction_method = Column(String, default="NOT_IMPLEMENTED")
    ocr_status = Column(String, default="OCR_NOT_AVAILABLE")
    extracted_text = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    sensitivity = Column(SAEnum(Sensitivity), default=Sensitivity.INTERNAL)

    case = relationship("Case", back_populates="documents")


class Fact(Base):
    __tablename__ = "facts"
    id = Column(String, primary_key=True, default=lambda: gen_id("fact"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    label = Column(String, nullable=False)  # short field name, e.g. "notice_date"
    statement = Column(Text, nullable=False)  # human readable fact text
    status = Column(SAEnum(FactStatus), default=FactStatus.UNKNOWN)
    sensitivity = Column(SAEnum(Sensitivity), default=Sensitivity.INTERNAL)
    source_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    source_excerpt = Column(String, nullable=True)
    confidence = Column(String, nullable=True)  # low | medium | high — never a fabricated %
    provenance_id = Column(String, default=lambda: gen_id("prov"))
    superseded_by_id = Column(String, ForeignKey("facts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="facts")
    source_document = relationship("Document", foreign_keys=[source_document_id])


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id = Column(String, primary_key=True, default=lambda: gen_id("evt"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    event_date = Column(String, nullable=True)  # ISO date string; may be NOT_PROVIDED
    description = Column(Text, nullable=False)
    source_type = Column(String, default="USER_REPORTED")  # USER_REPORTED | DOCUMENT_SUPPORTED
    source_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    related_fact_id = Column(String, ForeignKey("facts.id"), nullable=True)

    case = relationship("Case", back_populates="timeline_events")


class Deadline(Base):
    __tablename__ = "deadlines"
    id = Column(String, primary_key=True, default=lambda: gen_id("dl"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(String, nullable=True)
    status = Column(SAEnum(FactStatus), default=FactStatus.USER_REPORTED)

    case = relationship("Case", back_populates="deadlines")


class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, default=lambda: gen_id("q"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    text = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    priority = Column(String, default="medium")  # low | medium | high
    resolved = Column(Boolean, default=False)

    case = relationship("Case", back_populates="questions")


class Conflict(Base):
    __tablename__ = "conflicts"
    id = Column(String, primary_key=True, default=lambda: gen_id("conf"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    conflict_type = Column(SAEnum(ConflictType), nullable=False)
    description = Column(Text, nullable=False)
    fact_ids = Column(JSON, default=list)
    resolved = Column(Boolean, default=False)
    resolution_note = Column(Text, nullable=True)

    case = relationship("Case", back_populates="conflicts")


class Handoff(Base):
    __tablename__ = "handoffs"
    id = Column(String, primary_key=True, default=lambda: gen_id("ho"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    purpose = Column(String, nullable=False)
    recipient_role = Column(SAEnum(Role), nullable=False)
    sender_role = Column(SAEnum(Role), nullable=False)
    state = Column(SAEnum(HandoffState), default=HandoffState.DRAFT)
    current_version_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="handoffs")
    versions = relationship("HandoffVersion", back_populates="handoff", cascade="all, delete-orphan",
                             order_by="HandoffVersion.version_number")


class HandoffVersion(Base):
    __tablename__ = "handoff_versions"
    id = Column(String, primary_key=True, default=lambda: gen_id("hov"))
    handoff_id = Column(String, ForeignKey("handoffs.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    # Snapshot of packet contents at this version (ids only; resolved at read time)
    included_fact_ids = Column(JSON, default=list)
    included_document_ids = Column(JSON, default=list)
    included_timeline_event_ids = Column(JSON, default=list)
    included_deadline_ids = Column(JSON, default=list)
    included_question_ids = Column(JSON, default=list)
    included_conflict_ids = Column(JSON, default=list)
    excluded_field_notes = Column(JSON, default=list)  # [{field, reason}]
    quality_checks = Column(JSON, default=dict)  # explicit ✓/⚠ checklist, never a black-box score
    risk_flags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_role = Column(SAEnum(Role), nullable=True)

    handoff = relationship("Handoff", back_populates="versions")
    acknowledgement = relationship("Acknowledgement", back_populates="handoff_version", uselist=False)
    clarifications = relationship("Clarification", back_populates="handoff_version")


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String, primary_key=True, default=lambda: gen_id("appr"))
    handoff_version_id = Column(String, ForeignKey("handoff_versions.id"), nullable=False)
    approved_by_role = Column(SAEnum(Role), nullable=False)
    decision = Column(String, nullable=False)  # APPROVE | EDIT | REJECT
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Acknowledgement(Base):
    __tablename__ = "acknowledgements"
    id = Column(String, primary_key=True, default=lambda: gen_id("ack"))
    handoff_version_id = Column(String, ForeignKey("handoff_versions.id"), nullable=False)
    action = Column(String, nullable=False)  # ACKNOWLEDGE | REQUEST_CLARIFICATION | RETURN_FOR_CORRECTION | ACCEPT
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    handoff_version = relationship("HandoffVersion", back_populates="acknowledgement")


class Clarification(Base):
    __tablename__ = "clarifications"
    id = Column(String, primary_key=True, default=lambda: gen_id("clar"))
    handoff_version_id = Column(String, ForeignKey("handoff_versions.id"), nullable=False)
    question = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    handoff_version = relationship("HandoffVersion", back_populates="clarifications")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(String, primary_key=True, default=lambda: gen_id("run"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    agent_name = Column(String, nullable=False)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    provider = Column(String, default="MOCK")
    latency_ms = Column(Integer, nullable=True)
    correlation_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=lambda: gen_id("audit"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    actor = Column(String, default="system")
    role = Column(String, nullable=True)
    event = Column(String, nullable=False)
    result = Column(String, default="ok")
    correlation_id = Column(String, nullable=True)
    source = Column(String, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="audit_events")
