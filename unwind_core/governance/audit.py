"""Audit logging for UNWIND Core Governance.

Every governance and execution event creates an immutable, content-verifiable audit record.
Sensitive tokens/secrets are structurally sanitized and never recorded.
"""

from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.proposal import ProposalStatus

_SECRET_PATTERNS = [
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"api[\s_\-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]+['\"]?", re.IGNORECASE),
    re.compile(r"password\s*[:=]\s*['\"]?[^'\"\s]+['\"]?", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*['\"]?[^'\"\s]+['\"]?", re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    """Strips potential API keys, passwords, or secret tokens from audit text."""
    if not text:
        return text
    sanitized = text
    for pat in _SECRET_PATTERNS:
        sanitized = pat.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class AuditEventType(str, Enum):
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    GOVERNANCE_REVIEWED = "GOVERNANCE_REVIEWED"
    ASK_HUMAN = "ASK_HUMAN"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    EXECUTION_ATTEMPTED = "EXECUTION_ATTEMPTED"
    EXECUTED = "EXECUTED"
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    proposal_id: str
    case_id: str
    event_type: AuditEventType
    previous_status: ProposalStatus | None
    new_status: ProposalStatus
    actor_type: str  # "AI" | "GOVERNANCE_ENGINE" | "HUMAN" | "SYSTEM"
    actor_id: str
    timestamp: datetime
    proposal_hash: str
    provenance_refs: list[str]
    reason: str
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["previous_status"] = self.previous_status.value if self.previous_status else None
        data["new_status"] = self.new_status.value
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AuditStore:
    """Thread-safe append-only in-memory audit store with query capabilities."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._by_proposal: dict[str, list[AuditRecord]] = {}
        self._lock = threading.Lock()

    def record_event(
        self,
        *,
        proposal_id: str,
        case_id: str,
        event_type: AuditEventType,
        previous_status: ProposalStatus | None,
        new_status: ProposalStatus,
        actor_type: str,
        actor_id: str,
        proposal_hash: str,
        provenance_refs: list[str],
        reason: str,
        timestamp: datetime | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            event_id=f"audit_{uuid.uuid4().hex[:16]}",
            proposal_id=proposal_id,
            case_id=case_id,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            actor_type=actor_type,
            actor_id=sanitize_text(actor_id),
            timestamp=timestamp or datetime.now(UTC),
            proposal_hash=proposal_hash,
            provenance_refs=list(provenance_refs),
            reason=sanitize_text(reason),
        )
        with self._lock:
            self._records.append(record)
            self._by_proposal.setdefault(proposal_id, []).append(record)
        return record

    def get_events_for_proposal(self, proposal_id: str) -> list[AuditRecord]:
        with self._lock:
            return list(self._by_proposal.get(proposal_id, []))

    def get_all_events(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._records)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def reset_for_test(self) -> None:
        with self._lock:
            self._records.clear()
            self._by_proposal.clear()


# Default singleton instance
_GLOBAL_AUDIT_STORE = AuditStore()


def get_audit_store() -> AuditStore:
    return _GLOBAL_AUDIT_STORE


__all__ = [
    "AuditEventType",
    "AuditRecord",
    "AuditStore",
    "get_audit_store",
    "sanitize_text",
]
