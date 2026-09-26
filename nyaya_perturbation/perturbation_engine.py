"""Legal Perturbation Lab coordinator for NYAYA-SATYA.

Applies controlled material and immaterial perturbations to cloned twins
to verify that case reasoning changes when it should, and stays stable when it should not.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.intervention import (
    Intervention,
    InterventionOperation,
    InterventionTargetType,
)
from nyaya_perturbation.perturbation_scenario import (
    PerturbationOutcome,
    PerturbationResultType,
    PerturbationScenario,
    PerturbationType,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class LegalPerturbationLab:
    """Coordinates perturbation experimentation over CaseDigitalTwin instances."""

    def __init__(self) -> None:
        self._blast_engine = BlastRadiusEngine()
        self._outcomes: dict[str, PerturbationOutcome] = {}

    def run_scenario(
        self,
        twin: CaseDigitalTwin,
        scenario: PerturbationScenario,
    ) -> PerturbationOutcome:
        """Run a perturbation scenario on an isolated clone of the twin."""
        canonical_pre_hash = twin.integrity_hash

        # Step 1: Deepcopy clone
        sim_twin = copy.deepcopy(twin)

        # Step 2: Formulate intervention from perturbation scenario
        op_str = scenario.operation.upper()
        if op_str == "REMOVE":
            op = InterventionOperation.REMOVE
        elif op_str == "MODIFY":
            op = InterventionOperation.CHANGE_VALUE
        elif op_str == "CORRUPT_TIMESTAMP":
            op = InterventionOperation.CHANGE_TIME
        else:
            op = InterventionOperation.MARK_CONTESTED

        target_type_str = scenario.target_node_type.upper()
        if target_type_str == "EVIDENCE":
            ttype = InterventionTargetType.EVIDENCE
        elif target_type_str == "CLAIM":
            ttype = InterventionTargetType.CLAIM
        elif target_type_str == "EVENT":
            ttype = InterventionTargetType.EVENT
        else:
            ttype = InterventionTargetType.ASSUMPTION

        intervention = Intervention(
            intervention_id=f"INT_PERT_{uuid.uuid4().hex[:8]}",
            case_id=twin.case_id,
            target_id=scenario.target_node_id,
            target_type=ttype,
            operation=op,
            rationale=scenario.rationale,
            hypothetical_state=scenario.parameters,
        )

        # Step 3: Compute blast radius on the clone
        report = self._blast_engine.compute(twin, intervention)

        observed_affected = sorted(
            list(
                set(
                    [e.node_id for e in report.direct_effects]
                    + [e.node_id for e in report.indirect_effects]
                )
            )
        )

        # Step 4: Compare expected vs observed
        missing_changes: list[str] = []
        unexpected_changes: list[str] = []

        if scenario.perturbation_type == PerturbationType.SHOULD_CHANGE:
            for exp in scenario.expected_affected_nodes:
                if exp not in observed_affected:
                    missing_changes.append(exp)

            if missing_changes:
                result_type = PerturbationResultType.EXPECTED_CHANGE_MISSING
                is_safe = False
                explanation = (
                    f"Material perturbation failed to trigger expected state changes on: {missing_changes}"
                )
            else:
                result_type = PerturbationResultType.EXPECTED_CHANGE
                is_safe = True
                explanation = "Material perturbation successfully propagated to all expected dependent nodes."

        else:  # SHOULD_NOT_CHANGE
            for prot in scenario.protected_nodes:
                if prot in observed_affected:
                    unexpected_changes.append(prot)

            if unexpected_changes:
                result_type = PerturbationResultType.UNEXPECTED_CHANGE
                is_safe = False
                explanation = (
                    f"Immaterial perturbation unexpectedly propagated to protected nodes: {unexpected_changes}"
                )
            else:
                result_type = PerturbationResultType.EXPECTED_NO_CHANGE
                is_safe = True
                explanation = "Immaterial perturbation was properly contained with zero unexpected propagation."

        # Step 5: Assert canonical twin immutability
        assert twin.integrity_hash == canonical_pre_hash, (
            "CRITICAL ARCHITECTURAL VIOLATION: Canonical twin mutated during perturbation run!"
        )

        outcome = PerturbationOutcome(
            scenario_id=scenario.scenario_id,
            case_id=twin.case_id,
            result_type=result_type,
            is_safe=is_safe,
            observed_affected_nodes=observed_affected,
            missing_expected_changes=missing_changes,
            unexpected_changes=unexpected_changes,
            explanation=explanation,
            pre_hash=canonical_pre_hash,
            post_hash=sim_twin.integrity_hash,
        )

        self._outcomes[scenario.scenario_id] = outcome
        return outcome

    def get_outcome(self, scenario_id: str) -> PerturbationOutcome | None:
        return self._outcomes.get(scenario_id)

    def list_outcomes(self, case_id: str | None = None) -> list[PerturbationOutcome]:
        if case_id:
            return [o for o in self._outcomes.values() if o.case_id == case_id]
        return list(self._outcomes.values())

    def reset_for_test(self) -> None:
        self._outcomes.clear()
