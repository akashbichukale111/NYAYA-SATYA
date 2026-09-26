"""Human Review Checklist model and management for NYAYA-SATYA Dossier 2.0.

Explicitly itemizes all pending legal obligations requiring human jurist decision.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ReviewSeverity(str, Enum):
    """Urgency / structural significance of a review item."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewStatus(str, Enum):
    """Lifecycle status of a human review checklist item."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    PENDING_HUMAN_DECISION = "PENDING_HUMAN_DECISION"


@dataclass
class ReviewItem:
    """An individual structured human review obligation item."""

    review_id: str
    severity: ReviewSeverity
    source: str  # e.g., 'unresolved_contradiction', 'unverified_authority', 'repair_gate'
    explanation: str
    recommended_action: str
    evidence_refs: list[str] = field(default_factory=list)
    status: ReviewStatus = ReviewStatus.OPEN
    assigned_to: str | None = None
    resolution_notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None

    def resolve(self, notes: str, actor: str) -> None:
        """Mark item as resolved by an authorized human actor."""
        self.status = ReviewStatus.RESOLVED
        self.resolution_notes = notes
        self.assigned_to = actor
        self.resolved_at = datetime.now(UTC)

    def reject(self, notes: str, actor: str) -> None:
        """Mark item as rejected by an authorized human actor."""
        self.status = ReviewStatus.REJECTED
        self.resolution_notes = notes
        self.assigned_to = actor
        self.resolved_at = datetime.now(UTC)

    def acknowledge(self, actor: str) -> None:
        """Acknowledge receipt of item by a jurist."""
        self.status = ReviewStatus.ACKNOWLEDGED
        self.assigned_to = actor

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "severity": self.severity.value,
            "source": self.source,
            "explanation": self.explanation,
            "recommended_action": self.recommended_action,
            "evidence_refs": list(self.evidence_refs),
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewItem:
        d = dict(data)
        if isinstance(d.get("severity"), str):
            d["severity"] = ReviewSeverity(d["severity"])
        if isinstance(d.get("status"), str):
            d["status"] = ReviewStatus(d["status"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if isinstance(d.get("resolved_at"), str):
            d["resolved_at"] = datetime.fromisoformat(d["resolved_at"])
        return cls(**d)


@dataclass
class HumanReviewChecklist:
    """The complete structured checklist of human review obligations for a case."""

    case_id: str
    dossier_id: str
    items: list[ReviewItem] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def pending_count(self) -> int:
        return sum(
            1 for item in self.items
            if item.status in (ReviewStatus.OPEN, ReviewStatus.ACKNOWLEDGED, ReviewStatus.PENDING_HUMAN_DECISION)
        )

    @property
    def resolved_count(self) -> int:
        return sum(
            1 for item in self.items
            if item.status in (ReviewStatus.RESOLVED, ReviewStatus.REJECTED)
        )

    @property
    def critical_count(self) -> int:
        return sum(
            1 for item in self.items
            if item.severity == ReviewSeverity.CRITICAL and item.status != ReviewStatus.RESOLVED
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "dossier_id": self.dossier_id,
            "total_count": self.total_count,
            "pending_count": self.pending_count,
            "resolved_count": self.resolved_count,
            "critical_count": self.critical_count,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HumanReviewChecklist:
        d = dict(data)
        items = [ReviewItem.from_dict(i) if isinstance(i, dict) else i for i in d.get("items", [])]
        return cls(case_id=d["case_id"], dossier_id=d["dossier_id"], items=items)
