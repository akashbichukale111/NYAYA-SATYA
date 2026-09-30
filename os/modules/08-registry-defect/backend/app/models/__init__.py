"""
SQLAlchemy domain models for the Registry Defect Engine.

Design rules enforced throughout:
- Every case-scoped entity carries case_id and is filtered by it at the
  query layer (see app/core/security.py) to guarantee case isolation.
- created_at/updated_at are set explicitly (UTC) rather than relying on
  DB-side defaults, so behavior is identical on SQLite and Postgres.
- Enums are stored as plain strings (not native DB enums) for portability
  and so UNKNOWN/new values never break migrations.
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.ids import new_id, utcnow


def _json_list():
    return Column(JSON, default=list)


def _json_dict():
    return Column(JSON, default=dict)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: new_id("user"))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    role = Column(String, nullable=False)  # UserRole
    hashed_password = Column(String, nullable=False)
    created_at = Column(String, default=lambda: utcnow().isoformat())
    is_active = Column(Boolean, default=True)


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=lambda: new_id("case"))
    title = Column(String, nullable=False)
    case_reference = Column(String, nullable=True)
    owner_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="ACTIVE")
    is_demo = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: utcnow().isoformat())
    updated_at = Column(String, default=lambda: utcnow().isoformat())

    filing_packages = relationship("FilingPackage", back_populates="case", cascade="all, delete-orphan")


class FilingPackage(Base):
    __tablename__ = "filing_packages"
    id = Column(String, primary_key=True, default=lambda: new_id("pkg"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    lifecycle_state = Column(String, default="DRAFT")  # FilingLifecycleState
    created_at = Column(String, default=lambda: utcnow().isoformat())
    updated_at = Column(String, default=lambda: utcnow().isoformat())

    case = relationship("Case", back_populates="filing_packages")
    documents = relationship("Document", back_populates="filing_package", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="filing_package", cascade="all, delete-orphan")
    checklist_items = relationship("ChecklistItem", back_populates="filing_package", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="filing_package", cascade="all, delete-orphan")
    objections = relationship("RegistryObjection", back_populates="filing_package", cascade="all, delete-orphan")


class FilingSubmission(Base):
    __tablename__ = "filing_submissions"
    id = Column(String, primary_key=True, default=lambda: new_id("sub"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    submitted_at = Column(String, default=lambda: utcnow().isoformat())
    submitted_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    snapshot_json = Column(JSON, default=dict)  # frozen state at submission time
    status = Column(String, default="RECORDED")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: new_id("doc"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    display_name = Column(String, nullable=False)
    document_kind = Column(String, nullable=True)  # e.g. petition, annexure, affidavit (user/label supplied)
    current_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    status = Column(String, default="ACTIVE")  # ACTIVE / SUPERSEDED / QUARANTINED
    created_at = Column(String, default=lambda: utcnow().isoformat())
    updated_at = Column(String, default=lambda: utcnow().isoformat())

    filing_package = relationship("FilingPackage", back_populates="documents", foreign_keys=[filing_package_id])
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan",
                             foreign_keys="DocumentVersion.document_id")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(String, primary_key=True, default=lambda: new_id("docv"))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    original_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    detected_format = Column(String, nullable=True)  # DocumentFormat
    size_bytes = Column(Integer, default=0)
    sha256 = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    extraction_status = Column(String, default="PENDING")  # PENDING/OK/FAILED
    extraction_error = Column(String, nullable=True)
    page_count = Column(Integer, nullable=True)
    quarantined = Column(Boolean, default=False)
    quarantine_reason = Column(String, nullable=True)
    uploaded_at = Column(String, default=lambda: utcnow().isoformat())
    uploaded_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    source_location_known = Column(Boolean, default=False)

    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])
    metadata_entries = relationship("DocumentMetadata", back_populates="document_version", cascade="all, delete-orphan")
    sections = relationship("DocumentSection", back_populates="document_version", cascade="all, delete-orphan")


class DocumentSection(Base):
    """A coarse structural unit of a parsed document (e.g., a page or a
    paragraph block) used to give evidence citations a real, non-fabricated
    location when one can be determined."""
    __tablename__ = "document_sections"
    id = Column(String, primary_key=True, default=lambda: new_id("sec"))
    document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    section_type = Column(String, default="PAGE")  # PAGE / PARAGRAPH / ROW
    section_index = Column(Integer, nullable=True)  # 0-based; None if unknown
    text_excerpt = Column(Text, nullable=True)
    location_known = Column(Boolean, default=False)

    document_version = relationship("DocumentVersion", back_populates="sections")


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"
    id = Column(String, primary_key=True, default=lambda: new_id("meta"))
    document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False, index=True)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    field_name = Column(String, nullable=False)  # e.g. case_number, party_name, document_date
    field_value = Column(String, nullable=True)
    source = Column(String, default="EXTRACTED")  # EXTRACTED / USER_PROVIDED
    confidence = Column(String, default="UNVERIFIED")  # VerificationStatus

    document_version = relationship("DocumentVersion", back_populates="metadata_entries")


class RequirementSet(Base):
    __tablename__ = "requirement_sets"
    id = Column(String, primary_key=True, default=lambda: new_id("rset"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # RequirementSourceType
    source_reference = Column(String, nullable=True)
    imported_at = Column(String, default=lambda: utcnow().isoformat())


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(String, primary_key=True, default=lambda: new_id("req"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    requirement_set_id = Column(String, ForeignKey("requirement_sets.id"), nullable=True)
    requirement_type = Column(String, nullable=False)  # RequirementType
    description = Column(Text, nullable=False)
    source = Column(String, nullable=False)  # RequirementSourceType
    source_reference = Column(String, nullable=True)  # e.g. "User checklist item 3" or "Uploaded checklist.pdf"
    version = Column(Integer, default=1)
    effective_from = Column(String, nullable=True)
    effective_until = Column(String, nullable=True)
    jurisdiction = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")  # RequirementStatus
    verification_status = Column(String, default="UNVERIFIED")  # VerificationStatus
    target_reference_label = Column(String, nullable=True)  # e.g. "Annexure B" — what it names, if a named item
    created_at = Column(String, default=lambda: utcnow().isoformat())
    updated_at = Column(String, default=lambda: utcnow().isoformat())

    filing_package = relationship("FilingPackage", back_populates="requirements")
    checklist_items = relationship("ChecklistItem", back_populates="requirement", cascade="all, delete-orphan")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id = Column(String, primary_key=True, default=lambda: new_id("chk"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    requirement_id = Column(String, ForeignKey("requirements.id"), nullable=False, index=True)
    status = Column(String, default="UNKNOWN")  # ChecklistItemStatus
    source = Column(String, nullable=True)
    document_refs = Column(JSON, default=list)   # list of document ids
    evidence_refs = Column(JSON, default=list)   # list of evidence descriptor dicts
    verification = Column(String, default="UNVERIFIED")
    review_state = Column(String, default="NOT_REVIEWED")
    explanation = Column(Text, nullable=True)  # WHY this status was assigned
    updated_at = Column(String, default=lambda: utcnow().isoformat())

    filing_package = relationship("FilingPackage", back_populates="checklist_items")
    requirement = relationship("Requirement", back_populates="checklist_items")


class AttachmentReference(Base):
    """A reference to another item (annexure, exhibit, schedule...)
    detected inside a document's extracted text."""
    __tablename__ = "attachment_references"
    id = Column(String, primary_key=True, default=lambda: new_id("aref"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    source_document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    reference_label = Column(String, nullable=False)  # e.g. "Annexure B"
    reference_type = Column(String, default="UNKNOWN")  # ANNEXURE / EXHIBIT / SCHEDULE / OTHER
    raw_context = Column(Text, nullable=True)  # the sentence/snippet it was found in
    section_id = Column(String, ForeignKey("document_sections.id"), nullable=True)
    location_known = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    resolved_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    created_at = Column(String, default=lambda: utcnow().isoformat())


class AttachmentRequirement(Base):
    """Links an AttachmentReference to the requirement it satisfies or
    violates, when applicable."""
    __tablename__ = "attachment_requirements"
    id = Column(String, primary_key=True, default=lambda: new_id("areq"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    attachment_reference_id = Column(String, ForeignKey("attachment_references.id"), nullable=False)
    requirement_id = Column(String, ForeignKey("requirements.id"), nullable=True)


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"
    id = Column(String, primary_key=True, default=lambda: new_id("dupg"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    duplicate_type = Column(String, nullable=False)  # DuplicateType
    member_document_version_ids = Column(JSON, default=list)
    similarity_evidence = Column(Text, nullable=True)
    original_document_version_id = Column(String, nullable=True)  # human-confirmed original, if set
    reviewed = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: utcnow().isoformat())


class Conflict(Base):
    """A detected metadata/informational conflict between two or more
    documents. The engine records both sides; it does not decide which
    is correct."""
    __tablename__ = "conflicts"
    id = Column(String, primary_key=True, default=lambda: new_id("conf"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    conflict_type = Column(String, nullable=False)  # e.g. METADATA_CONFLICT
    field_name = Column(String, nullable=True)
    left_document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    left_value = Column(String, nullable=True)
    right_document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    right_value = Column(String, nullable=True)
    status = Column(String, default="UNRESOLVED")  # UNRESOLVED / HUMAN_RESOLVED
    resolution_note = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: utcnow().isoformat())


class Supersession(Base):
    __tablename__ = "supersessions"
    id = Column(String, primary_key=True, default=lambda: new_id("sup"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    predecessor_document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    successor_document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=False)
    relationship_type = Column(String, default="SUPERSEDES")  # VersionRelationship
    confirmed_by_human = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: utcnow().isoformat())


class Verification(Base):
    __tablename__ = "verifications"
    id = Column(String, primary_key=True, default=lambda: new_id("ver"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    target_type = Column(String, nullable=False)  # DEFECT / REQUIREMENT / CORRECTION
    target_id = Column(String, nullable=False)
    result = Column(String, default="PENDING")  # PENDING / VERIFIED / STILL_FAILING / UNKNOWN
    notes = Column(Text, nullable=True)
    verified_at = Column(String, default=lambda: utcnow().isoformat())
    verified_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)


class DefectEvidence(Base):
    __tablename__ = "defect_evidence"
    id = Column(String, primary_key=True, default=lambda: new_id("evid"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    defect_id = Column(String, ForeignKey("defects.id"), nullable=False, index=True)
    document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    section_id = Column(String, ForeignKey("document_sections.id"), nullable=True)
    requirement_id = Column(String, ForeignKey("requirements.id"), nullable=True)
    excerpt = Column(Text, nullable=True)
    location_known = Column(Boolean, default=False)
    location_label = Column(String, nullable=True)  # e.g. "page 3" only if actually known


class Defect(Base):
    __tablename__ = "defects"
    id = Column(String, primary_key=True, default=lambda: new_id("dft"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    defect_type = Column(String, nullable=False)  # DefectType
    category = Column(String, nullable=False)  # derived from DEFECT_CATEGORY_MAP
    severity = Column(String, default="ATTENTION")  # DefectSeverity
    status = Column(String, default="DETECTED")  # DefectLifecycleState
    description = Column(Text, nullable=False)
    source_refs = Column(JSON, default=list)
    document_refs = Column(JSON, default=list)
    requirement_refs = Column(JSON, default=list)
    detected_by = Column(String, default="SYSTEM")  # agent name
    detected_at = Column(String, default=lambda: utcnow().isoformat())
    verification_status = Column(String, default="SYSTEM_DETECTED")  # VerificationStatus
    human_review_required = Column(Boolean, default=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(String, nullable=True)

    filing_package = relationship("FilingPackage", back_populates="defects")
    evidence = relationship("DefectEvidence", cascade="all, delete-orphan",
                             primaryjoin="Defect.id==DefectEvidence.defect_id")


class DefectResolution(Base):
    __tablename__ = "defect_resolutions"
    id = Column(String, primary_key=True, default=lambda: new_id("dres"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    defect_id = Column(String, ForeignKey("defects.id"), nullable=False, index=True)
    resolution_type = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    resolved_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(String, default=lambda: utcnow().isoformat())
    verified = Column(Boolean, default=False)


class RegistryObjection(Base):
    __tablename__ = "registry_objections"
    id = Column(String, primary_key=True, default=lambda: new_id("obj"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    original_text = Column(Text, nullable=False)  # preserved verbatim
    source_reference = Column(String, nullable=True)
    status = Column(String, default="OPEN")  # ObjectionStatus
    linked_defect_id = Column(String, ForeignKey("defects.id"), nullable=True)
    created_at = Column(String, default=lambda: utcnow().isoformat())
    updated_at = Column(String, default=lambda: utcnow().isoformat())

    filing_package = relationship("FilingPackage", back_populates="objections")


class CorrectionRequest(Base):
    __tablename__ = "correction_requests"
    id = Column(String, primary_key=True, default=lambda: new_id("creq"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    defect_id = Column(String, ForeignKey("defects.id"), nullable=True)
    objection_id = Column(String, ForeignKey("registry_objections.id"), nullable=True)
    description = Column(Text, nullable=False)
    suggested_action = Column(String, nullable=True)  # ActionProposalType
    status = Column(String, default="PLANNED")  # PLANNED / SUBMITTED / VERIFICATION_PENDING / RESOLVED
    created_at = Column(String, default=lambda: utcnow().isoformat())


class CorrectionSubmission(Base):
    __tablename__ = "correction_submissions"
    id = Column(String, primary_key=True, default=lambda: new_id("csub"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    correction_request_id = Column(String, ForeignKey("correction_requests.id"), nullable=False)
    document_version_id = Column(String, ForeignKey("document_versions.id"), nullable=True)
    note = Column(Text, nullable=True)
    submitted_at = Column(String, default=lambda: utcnow().isoformat())
    submitted_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    simulated = Column(Boolean, default=True)  # corrections are simulated, not filed with any real registry


class ReviewTask(Base):
    __tablename__ = "review_tasks"
    id = Column(String, primary_key=True, default=lambda: new_id("rev"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=True)
    target_type = Column(String, nullable=False)  # DEFECT / CONFLICT / REQUIREMENT / CORRECTION / EXPORT / ACTION
    target_id = Column(String, nullable=False)
    action_requested = Column(String, nullable=False)  # e.g. CONFIRM_DEFECT, APPROVE_CORRECTION
    decision = Column(String, default="PENDING")  # ReviewDecision
    decided_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    decided_at = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: utcnow().isoformat())


class ActionProposal(Base):
    __tablename__ = "action_proposals"
    id = Column(String, primary_key=True, default=lambda: new_id("act"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)  # ActionProposalType
    reason = Column(Text, nullable=False)
    source_refs = Column(JSON, default=list)
    affected_items = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    verification_required = Column(Boolean, default=True)
    human_approval_required = Column(Boolean, default=True)
    status = Column(String, default="PROPOSED")  # PROPOSED / APPROVED / REJECTED / EXECUTED_SIMULATION
    created_at = Column(String, default=lambda: utcnow().isoformat())


class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(String, primary_key=True, default=lambda: new_id("sim"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    filing_package_id = Column(String, ForeignKey("filing_packages.id"), nullable=False, index=True)
    simulation_type = Column(String, nullable=False)  # CRASH_TEST / COUNTERFACTUAL
    scenario = Column(String, nullable=False)
    input_params = Column(JSON, default=dict)
    result_json = Column(JSON, default=dict)
    is_destructive = Column(Boolean, default=False)  # always False; simulations never mutate real state
    run_at = Column(String, default=lambda: utcnow().isoformat())
    run_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=lambda: new_id("aud"))
    case_id = Column(String, nullable=True, index=True)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    actor_role = Column(String, nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(String, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    timestamp = Column(String, default=lambda: utcnow().isoformat())
    provenance = Column(String, nullable=True)


class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"
    id = Column(String, primary_key=True, default=lambda: new_id("prov"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    origin = Column(String, nullable=False)  # e.g. UPLOAD / USER_INPUT / SYSTEM_DERIVED / IMPORTED
    origin_detail = Column(Text, nullable=True)
    recorded_at = Column(String, default=lambda: utcnow().isoformat())
