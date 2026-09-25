"""Attack Scenario Validator for NYAYA-SATYA.

Validates that attack scenarios conform to schema specifications,
contain explicit premises, and target existing case nodes.
"""

from __future__ import annotations

import re
from typing import Any

from nyaya_adversarial.contracts.attack import AttackScenario, AttackType
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class AttackValidationError(ValueError):
    """Raised when an AttackScenario fails validation checks."""


class AttackValidator:
    """Validates AttackScenarios prior to execution."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id

    def validate_scenario(self, scenario: AttackScenario) -> None:
        """Asserts scenario correctness against case boundary and integrity rules."""
        if scenario.case_id != self.case_id:
            raise AttackValidationError(
                f"Cross-case attack prohibited: scenario case={scenario.case_id} != twin case={self.case_id}"
            )

        if not scenario.attack_id or not scenario.attack_id.strip():
            raise AttackValidationError("attack_id cannot be blank")

        if not scenario.premise or len(scenario.premise.strip()) < 5:
            raise AttackValidationError("Attack scenario must provide a substantive premise (>5 chars)")

        if not scenario.attack_question or not scenario.attack_question.strip().endswith("?"):
            raise AttackValidationError("attack_question must be a non-empty string ending with '?'")

        # Validate target node exists in twin
        target_id = scenario.target_node_id
        target_type = scenario.target_node_type

        if target_type == "CLAIM" and target_id not in self.twin.claims:
            raise AttackValidationError(f"Target claim {target_id} not found in case {self.case_id}")
        elif target_type == "EVIDENCE" and target_id not in self.twin.evidence_refs:
            raise AttackValidationError(f"Target evidence {target_id} not found in case {self.case_id}")
        elif target_type == "ENTITY" and target_id not in self.twin.entities:
            raise AttackValidationError(f"Target entity {target_id} not found in case {self.case_id}")
        elif target_type == "ISSUE" and target_id not in self.twin.issues:
            raise AttackValidationError(f"Target issue {target_id} not found in case {self.case_id}")
        elif target_type == "EVENT" and target_id not in self.twin.events:
            raise AttackValidationError(f"Target event {target_id} not found in case {self.case_id}")
