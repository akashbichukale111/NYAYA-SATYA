"""Intervention validator for NYAYA-SATYA.

Validates interventions before execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.intervention import Intervention, InterventionTargetType
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


@dataclass
class InterventionValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


class InterventionValidator:
    """Validates intervention feasibility against the twin."""

    def validate(
        self, intervention: Intervention, twin: CaseDigitalTwin
    ) -> InterventionValidationResult:
        result = InterventionValidationResult()

        if intervention.case_id != twin.case_id:
            result.errors.append(
                f"Intervention case_id {intervention.case_id} != twin case_id {twin.case_id}"
            )
            result.valid = False

        target = intervention.target_id
        tt = intervention.target_type

        if tt == InterventionTargetType.EVIDENCE:
            if target not in twin.evidence_refs:
                result.errors.append(f"Evidence {target} not found in twin")
                result.valid = False
        elif tt == InterventionTargetType.CLAIM:
            if target not in twin.claims:
                result.errors.append(f"Claim {target} not found in twin")
                result.valid = False
        elif tt == InterventionTargetType.EVENT:
            if target not in twin.events:
                result.errors.append(f"Event {target} not found in twin")
                result.valid = False
        elif tt == InterventionTargetType.ENTITY:
            if target not in twin.entities:
                result.errors.append(f"Entity {target} not found in twin")
                result.valid = False

        return result
