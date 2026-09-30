import enum


class RoleName(str, enum.Enum):
    CITIZEN = "citizen"
    LEGAL_AID = "legal_aid"
    PARALEGAL = "paralegal"
    ADVOCATE = "advocate"
    ADMIN = "admin"


class CaseStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    ARCHIVED = "archived"


class MembershipRole(str, enum.Enum):
    OWNER = "owner"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class AttentionPriority(str, enum.Enum):
    INFO = "INFO"
    ATTENTION = "ATTENTION"
    HIGH_ATTENTION = "HIGH_ATTENTION"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class AttentionType(str, enum.Enum):
    CASE_CHANGED = "CASE_CHANGED"
    NEW_BLOCKER = "NEW_BLOCKER"
    EVIDENCE_GAP = "EVIDENCE_GAP"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    OBLIGATION_PENDING = "OBLIGATION_PENDING"
    TRACKED_DATE_APPROACHING = "TRACKED_DATE_APPROACHING"
    PAST_TRACKED_DATE = "PAST_TRACKED_DATE"
    REGISTRY_DEFECT = "REGISTRY_DEFECT"
    LIBERTY_REVIEW_ITEM = "LIBERTY_REVIEW_ITEM"
    HEARING_READINESS_BLOCKER = "HEARING_READINESS_BLOCKER"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    HANDOFF_PENDING = "HANDOFF_PENDING"
    WORKFLOW_BLOCKED = "WORKFLOW_BLOCKED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    PROVENANCE_GAP = "PROVENANCE_GAP"
    STALE_CASE_STATE = "STALE_CASE_STATE"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class AttentionStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SourceEngine(str, enum.Enum):
    EVIDENCE_DEPENDENCY = "evidence_dependency_engine"
    PROCEDURAL_OBLIGATION = "procedural_obligation_engine"
    CASE_CONTINUITY = "case_continuity_engine"
    CASE_BOTTLENECK = "case_bottleneck_engine"
    HEARING_READINESS = "hearing_readiness_engine"
    LEGAL_AID_HANDOFF = "legal_aid_handoff_engine"
    REGISTRY_DEFECT = "registry_defect_engine"
    UNDERTRIAL_LIBERTY_SENTINEL = "undertrial_liberty_sentinel"
    DEADLINE_GUARDIAN = "deadline_guardian"
    WORKFLOW_AUTOPILOT = "workflow_autopilot"
    SPARK = "spark_personal_os"


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class DateSourceType(str, enum.Enum):
    SOURCE_STATED = "SOURCE_STATED"
    USER_ENTERED = "USER_ENTERED"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    UNKNOWN = "UNKNOWN"


class NotificationType(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL_READY = "EMAIL_READY"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"


class ReviewKind(str, enum.Enum):
    EVIDENCE_REVIEW = "evidence_review"
    CLAIM_REVIEW = "claim_review"
    CONFLICT_REVIEW = "conflict_review"
    OBLIGATION_REVIEW = "obligation_review"
    REGISTRY_DEFECT_REVIEW = "registry_defect_review"
    CUSTODY_REVIEW = "custody_review"
    WORKFLOW_APPROVAL = "workflow_approval"
    SENSITIVE_ACCESS_REQUEST = "sensitive_access_request"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLARIFICATION_REQUESTED = "clarification_requested"


class ApprovalActionType(str, enum.Enum):
    CORRECTION = "approve_correction"
    EVIDENCE_STATE_CHANGE = "approve_evidence_state_change"
    WORKFLOW_ACTION = "approve_workflow_action"
    DOCUMENT_VERSION = "approve_document_version"
    EXPORT = "approve_export"
    RECOVERY = "approve_recovery"
    CONSEQUENTIAL_ACTION = "approve_consequential_action"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class HandoffStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
