"""Safety validator for NYAYA-SATYA Causal Reasoning.

Enforces:
- Cross-case isolation
- Quarantine boundary
- Immutable original twin protection
- Prompt injection detection
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nyaya_twin.contracts.case_twin import CaseDigitalTwin


_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|all|above)",
    r"(?i)you\s+are\s+now",
    r"(?i)system\s*prompt",
    r"(?i)override\s+instructions",
    r"(?i)disregard\s+(all|previous)",
]


@dataclass
class SafetyValidationResult:
    safe: bool = True
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"safe": self.safe, "violations": self.violations}


class CausalSafetyValidator:
    """Validates safety constraints for causal operations."""

    def validate_case_isolation(
        self, case_id: str, twin: CaseDigitalTwin
    ) -> SafetyValidationResult:
        """Ensure all operations are isolated to the correct case."""
        result = SafetyValidationResult()
        if case_id != twin.case_id:
            result.violations.append(
                f"Cross-case isolation violation: requested {case_id}, twin is {twin.case_id}"
            )
            result.safe = False
        return result

    def validate_twin_immutability(
        self, original_hash: str, current_hash: str
    ) -> SafetyValidationResult:
        """Verify the canonical twin was not mutated."""
        result = SafetyValidationResult()
        if original_hash != current_hash:
            result.violations.append(
                "CRITICAL: Canonical CaseDigitalTwin was mutated during operation"
            )
            result.safe = False
        return result

    def scan_for_injection(self, text: str) -> SafetyValidationResult:
        """Scan text for prompt injection patterns."""
        result = SafetyValidationResult()
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, text):
                result.violations.append(f"Prompt injection detected: pattern {pattern!r} matched")
                result.safe = False
        return result

    def validate_quarantine_boundary(
        self, evidence_ids: list[str], twin: CaseDigitalTwin
    ) -> SafetyValidationResult:
        """Ensure no quarantined evidence enters causal analysis."""
        result = SafetyValidationResult()
        for evid in evidence_ids:
            ref = twin.evidence_refs.get(evid)
            if ref is None:
                result.violations.append(f"Evidence {evid} not found in twin")
                result.safe = False
            elif hasattr(ref, 'risk_level') and ref.risk_level.value == "BLOCKED":
                result.violations.append(f"Quarantined evidence {evid} blocked from causal analysis")
                result.safe = False
        return result
