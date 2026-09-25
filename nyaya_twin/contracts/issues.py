"""Issue contracts for NYAYA-SATYA Case Digital Twin.

Models substantive disputes, legal questions, and points for judicial determination.
Does NOT automatically decide or resolve issues.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    CONFLICTED = "CONFLICTED"
    UNRESOLVED = "UNRESOLVED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"


@dataclass
class Issue:
    """A legal or factual dispute issue requiring human determination."""

    issue_id: str
    case_id: str
    title: str
    description: str = ""
    related_claim_ids: list[str] = field(default_factory=list)
    related_evidence_ids: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    status: IssueStatus = IssueStatus.OPEN
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.issue_id or not self.issue_id.strip():
            raise ValueError("issue_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.issue_id):
            raise ValueError(f"Invalid issue_id format: {self.issue_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Issue:
        d = dict(data)
        if isinstance(d.get("status"), str):
            d["status"] = IssueStatus(d["status"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if isinstance(d.get("updated_at"), str):
            d["updated_at"] = datetime.fromisoformat(d["updated_at"])
        if "provenance_refs" in d:
            d["provenance_refs"] = [
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            ]
        return cls(**d)
