"""Master repair validator for NYAYA-SATYA Auto-Healer.

Validates:
- Non-adjudication compliance (rejects prohibited terms like 'guilty', 'verdict', etc.)
- Prompt injection defense
- Case isolation
- Schema consistency
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.contracts.repair_constraint import RepairConstraints
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|all|above)",
    r"(?i)you\s+are\s+now",
    r"(?i)system\s*prompt",
    r"(?i)override\s+instructions",
    r"(?i)disregard\s+(all|previous)",
    r"(?i)approve\s+this\s+repair\s+automatically",
    r"(?i)bypass\s+governance",
    r"(?i)bypass\s+gate",
]


@dataclass
class RepairValidationResult:
    """Outcome of validating a repair candidate."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    non_adjudication_passed: bool = True
    injection_safe: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "non_adjudication_passed": self.non_adjudication_passed,
            "injection_safe": self.injection_safe,
        }


class RepairValidator:
    """Master validation engine for repair proposals."""

    def __init__(self, constraints: RepairConstraints | None = None) -> None:
        self.constraints = constraints or RepairConstraints()

    def validate(
        self,
        repair: RepairCandidate,
        twin: CaseDigitalTwin,
    ) -> RepairValidationResult:
        """Validate a repair proposal against structural and safety rules."""
        result = RepairValidationResult()

        # 1. Cross-case boundary validation
        if repair.case_id != twin.case_id:
            result.errors.append(
                f"Cross-case isolation violation: repair case_id '{repair.case_id}' != twin case_id '{twin.case_id}'"
            )
            result.is_valid = False

        # 2. Non-adjudication lexicon scan
        texts_to_scan = [
            repair.rationale,
            str(repair.proposed_change),
        ] + repair.expected_effects + repair.risk_flags

        combined_text = " ".join(texts_to_scan).lower()
        for term in self.constraints.prohibited_terms:
            if term.lower() in combined_text:
                result.errors.append(
                    f"Non-adjudication safety violation: prohibited term '{term}' detected in repair proposal"
                )
                result.non_adjudication_passed = False
                result.is_valid = False

        # 3. Prompt injection detection
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, combined_text):
                result.errors.append(
                    f"Prompt injection pattern detected: '{pattern}'"
                )
                result.injection_safe = False
                result.is_valid = False

        # 4. Target existence check
        if repair.target_claim_id and repair.target_claim_id not in twin.claims:
            result.warnings.append(
                f"Target claim '{repair.target_claim_id}' not found in canonical twin"
            )

        return result
