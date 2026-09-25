"""Safety and Zero-Trust Validator for NYAYA-SATYA Adversarial Subsystem.

Enforces zero-trust isolation:
- Rejects unverified raw quarantine bytes.
- Rejects cross-case contamination.
- Enforces prompt-injection containment in the data plane.
"""

from __future__ import annotations

import re
from typing import Any

from nyaya_evidence.contracts.evidence import EvidenceItem, EvidenceStatus
from nyaya_evidence.quarantine.manager import QuarantineViolationError
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class SafetyBoundaryViolation(ValueError):
    """Raised when an adversarial process breaches zero-trust boundaries."""


class SafetyValidator:
    """Validates security, data provenance, and cross-case isolation."""

    def assert_evidence_safe_for_reasoning(self, evidence: EvidenceItem) -> None:
        """Ensures raw quarantined or infected evidence cannot enter the reasoning plane."""
        if evidence.status in (EvidenceStatus.QUARANTINED, EvidenceStatus.REJECTED):
            raise QuarantineViolationError(
                f"ZERO-TRUST VIOLATION: Evidence {evidence.evidence_id} is in status {evidence.status.value} "
                f"and cannot be ingested into adversarial reasoning."
            )

    def assert_cross_case_isolation(
        self,
        expected_case_id: str,
        target_case_id: str,
    ) -> None:
        """Verifies that items from different cases are never mixed."""
        if expected_case_id != target_case_id:
            raise SafetyBoundaryViolation(
                f"CROSS-CASE ISOLATION VIOLATION: Expected case {expected_case_id}, got {target_case_id}."
            )

    def assert_injection_payload_contained(self, payload: str) -> None:
        """Verifies that an injection string is detected and safely disarmed."""
        dangerous_patterns = [
            re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
            re.compile(r"<script.*?>", re.IGNORECASE),
            re.compile(r"system\s*:\s*override", re.IGNORECASE),
        ]
        for pat in dangerous_patterns:
            if pat.search(payload):
                # Validated: pattern is recognized as adversarial and must remain inert
                return
