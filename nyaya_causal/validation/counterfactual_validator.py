"""Counterfactual scenario validator for NYAYA-SATYA.

Validates scenario consistency and non-adjudication compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.scenario import CounterfactualScenario
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


# Prohibited verdict/outcome terms
_PROHIBITED_TERMS = frozenset({
    "guilty", "not guilty", "liable", "verdict", "innocent",
    "perjury", "fraud confirmed", "win probability",
    "conviction likelihood", "acquitted", "sentence",
    "punishment", "guilt probability",
})


@dataclass
class CounterfactualValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


class CounterfactualValidator:
    """Validates counterfactual scenarios."""

    def validate(
        self, scenario: CounterfactualScenario, twin: CaseDigitalTwin
    ) -> CounterfactualValidationResult:
        result = CounterfactualValidationResult()

        if scenario.case_id != twin.case_id:
            result.errors.append("Scenario case_id does not match twin case_id")
            result.valid = False

        if not scenario.intervention:
            result.errors.append("Scenario has no intervention")
            result.valid = False

        if scenario.intervention and scenario.intervention.case_id != scenario.case_id:
            result.errors.append("Intervention case_id does not match scenario case_id")
            result.valid = False

        # Non-adjudication compliance check
        self._check_non_adjudication(scenario, result)

        return result

    def _check_non_adjudication(
        self, scenario: CounterfactualScenario, result: CounterfactualValidationResult
    ) -> None:
        """Scan scenario text for prohibited verdict language."""
        texts_to_scan = [
            scenario.intervention.rationale,
            scenario.error_message,
        ]
        texts_to_scan.extend(scenario.assumptions)
        texts_to_scan.extend(scenario.preconditions)

        for text in texts_to_scan:
            if not text:
                continue
            lower = text.lower()
            for term in _PROHIBITED_TERMS:
                if term in lower:
                    result.errors.append(
                        f"Non-adjudication violation: prohibited term '{term}' found"
                    )
                    result.valid = False
