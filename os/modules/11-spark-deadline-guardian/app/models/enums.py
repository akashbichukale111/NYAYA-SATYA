"""
Controlled vocabularies for SPARK DEADLINE GUARDIAN.

These are the only states the system is allowed to assign to a date or
deadline. Nothing in this codebase should upgrade an UNVERIFIED or
SYSTEM_DERIVED date into a certain one just because a model produced it.
See Section 3 of the product spec: "Legal / Safety Boundary".
"""

from enum import Enum


class SourceType(str, Enum):
    COURT_ORDER = "COURT_ORDER"
    NOTICE = "NOTICE"
    FILING = "FILING"
    CORRESPONDENCE = "CORRESPONDENCE"
    UPLOADED_DOCUMENT = "UPLOADED_DOCUMENT"
    CASE_EVENT = "CASE_EVENT"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    EXTERNAL_WORKFLOW = "EXTERNAL_WORKFLOW"


class ProvenanceState(str, Enum):
    """How much trust a given date candidate has earned."""

    SOURCE_EXPLICIT = "SOURCE_EXPLICIT"          # literal date string found in source text
    SOURCE_RELATIVE = "SOURCE_RELATIVE"          # e.g. "within 30 days of service"
    USER_ENTERED = "USER_ENTERED"                # typed in directly by a human
    SYSTEM_DERIVED = "SYSTEM_DERIVED"            # computed from another deadline
    UNVERIFIED = "UNVERIFIED"                    # extracted but not confirmed by a human
    CONFLICTING = "CONFLICTING"                  # two+ sources disagree
    SUPERSEDED = "SUPERSEDED"                    # a later source replaced this date
    UNKNOWN = "UNKNOWN"                          # could not be resolved
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class DeadlineStatus(str, Enum):
    DRAFT = "DRAFT"                    # created, not yet reviewed
    PENDING_REVIEW = "PENDING_REVIEW"  # queued for human approval
    VERIFIED = "VERIFIED"              # human-confirmed
    ACTIVE = "ACTIVE"                  # verified and upcoming
    AT_RISK = "AT_RISK"                # upcoming + unresolved dependency/conflict
    SUPERSEDED = "SUPERSEDED"
    COMPLETED = "COMPLETED"
    MISSED = "MISSED"


class ConflictType(str, Enum):
    DATE_MISMATCH = "DATE_MISMATCH"            # two sources give different dates for same obligation
    SOURCE_SUPERSESSION = "SOURCE_SUPERSESSION"  # a newer document appears to replace an older one
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    MISSING_ANCHOR = "MISSING_ANCHOR"          # relative date has no resolvable anchor event


class ActionRiskLevel(str, Enum):
    """Used by the Safe Action Planner (Section 2) to gate autonomy."""

    INFORMATIONAL = "INFORMATIONAL"        # e.g. send a reminder — no approval needed
    LOW = "LOW"                            # e.g. create a draft calendar entry
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"  # e.g. mark a deadline verified, notify a case owner
    BLOCKED = "BLOCKED"                    # e.g. anything resembling legal filing/decision-making
