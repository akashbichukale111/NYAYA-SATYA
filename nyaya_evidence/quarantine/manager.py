"""Quarantine Manager for NYAYA-SATYA.

Guarantees evidence quarantine isolation:
Evidence cannot be read, parsed, or processed for reasoning until it safely
progresses from QUARANTINED -> SCANNING -> SANITIZED -> REGISTERED.
"""

from __future__ import annotations

import threading
from typing import Any

from nyaya_evidence.contracts.evidence import EvidenceItem, EvidenceStatus


class QuarantineViolationError(RuntimeError):
    """Raised when an operation attempts to bypass quarantine or perform an invalid state move."""


class QuarantineManager:
    """Controls quarantine lifecycle and access gates for evidence items."""

    # Allowed forward lifecycle transitions
    _VALID_TRANSITIONS: dict[EvidenceStatus, frozenset[EvidenceStatus]] = {
        EvidenceStatus.RECEIVED: frozenset({EvidenceStatus.QUARANTINED}),
        EvidenceStatus.QUARANTINED: frozenset({
            EvidenceStatus.SCANNING,
            EvidenceStatus.REJECTED,
            EvidenceStatus.CORRUPTED,
        }),
        EvidenceStatus.SCANNING: frozenset({
            EvidenceStatus.SANITIZED,
            EvidenceStatus.FLAGGED,
            EvidenceStatus.MALICIOUS,
            EvidenceStatus.SCAN_FAILED,
            EvidenceStatus.REJECTED,
        }),
        EvidenceStatus.SANITIZED: frozenset({
            EvidenceStatus.REGISTERED,
            EvidenceStatus.FLAGGED,
            EvidenceStatus.REJECTED,
        }),
        EvidenceStatus.REGISTERED: frozenset({
            EvidenceStatus.PARSED,
            EvidenceStatus.FLAGGED,
        }),
        EvidenceStatus.PARSED: frozenset({
            EvidenceStatus.FLAGGED,
        }),
        # Terminal / Blocked states
        EvidenceStatus.FLAGGED: frozenset({EvidenceStatus.REJECTED}),
        EvidenceStatus.MALICIOUS: frozenset(),
        EvidenceStatus.REJECTED: frozenset(),
        EvidenceStatus.CORRUPTED: frozenset(),
        EvidenceStatus.SCAN_FAILED: frozenset({EvidenceStatus.SCANNING, EvidenceStatus.REJECTED}),
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def advance_status(
        self,
        item: EvidenceItem,
        target_status: EvidenceStatus,
        *,
        reason: str,
    ) -> EvidenceStatus:
        """Transitions evidence through quarantine lifecycle. Fails on illegal transition."""
        with self._lock:
            current = item.status
            allowed = self._VALID_TRANSITIONS.get(current, frozenset())

            if target_status not in allowed:
                raise QuarantineViolationError(
                    f"Illegal quarantine transition from {current.value} to {target_status.value}. "
                    f"Reason: {reason}. Evidence cannot bypass mandatory quarantine scanning."
                )

            item.status = target_status
            item.quarantine_reason = reason
            return target_status

    def assert_accessible_for_reasoning(self, item: EvidenceItem) -> None:
        """Throws QuarantineViolationError if evidence is still quarantined or untrusted."""
        if not item.is_safe_for_reasoning:
            raise QuarantineViolationError(
                f"Access denied: Evidence {item.evidence_id} is in status {item.status.value}. "
                "Only REGISTERED or PARSED evidence may be cited in TARKA-VYUH reasoning."
            )

    def mark_scanning(self, item: EvidenceItem) -> None:
        self.advance_status(item, EvidenceStatus.SCANNING, reason="Security and adversarial scan initiated")

    def mark_sanitized(self, item: EvidenceItem, reason: str = "Scan passed without high risk") -> None:
        self.advance_status(item, EvidenceStatus.SANITIZED, reason=reason)

    def mark_registered(self, item: EvidenceItem, reason: str = "Quarantine released; evidence registered") -> None:
        self.advance_status(item, EvidenceStatus.REGISTERED, reason=reason)

    def mark_flagged(self, item: EvidenceItem, reason: str) -> None:
        self.advance_status(item, EvidenceStatus.FLAGGED, reason=f"Suspicious patterns detected: {reason}")

    def mark_malicious(self, item: EvidenceItem, reason: str) -> None:
        self.advance_status(item, EvidenceStatus.MALICIOUS, reason=f"Active threat detected: {reason}")


__all__ = [
    "QuarantineManager",
    "QuarantineViolationError",
]
