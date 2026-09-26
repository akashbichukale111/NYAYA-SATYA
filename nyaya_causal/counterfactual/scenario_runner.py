"""Scenario runner for NYAYA-SATYA Counterfactual Lab.

Executes a counterfactual scenario:
1. Validates the scenario.
2. Deep clones the twin.
3. Applies the intervention.
4. Computes blast-radius.
5. Produces before/after comparison.
6. Verifies canonical twin integrity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.scenario import CounterfactualScenario, ScenarioStatus
from nyaya_causal.counterfactual.intervention_engine import InterventionEngine
from nyaya_causal.counterfactual.twin_comparator import TwinComparator
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class ScenarioRunner:
    """Executes counterfactual scenarios in isolation."""

    def __init__(self) -> None:
        self._intervention_engine = InterventionEngine()
        self._blast_engine = BlastRadiusEngine()
        self._comparator = TwinComparator()

    def run(
        self,
        scenario: CounterfactualScenario,
        twin: CaseDigitalTwin,
    ) -> CounterfactualScenario:
        """Execute scenario against twin. Never mutates original twin."""
        original_hash = twin.integrity_hash

        try:
            scenario.status = ScenarioStatus.RUNNING

            # Apply intervention on isolated copy
            counterfactual_twin = self._intervention_engine.apply(
                twin, scenario.intervention
            )

            # Compute blast radius
            scenario.blast_radius = self._blast_engine.compute(
                twin, scenario.intervention
            )

            # Compare
            scenario.comparison = self._comparator.compare(
                twin,
                counterfactual_twin,
                base_scenario_id=f"BASE_{scenario.case_id}",
                counterfactual_scenario_id=scenario.scenario_id,
            )

            scenario.status = ScenarioStatus.COMPLETED
            scenario.completed_at = datetime.now(UTC)

        except Exception as e:
            scenario.status = ScenarioStatus.FAILED
            scenario.error_message = str(e)

        # Verify original twin integrity
        assert twin.integrity_hash == original_hash, (
            f"CRITICAL: Canonical twin mutated during scenario {scenario.scenario_id}"
        )

        return scenario
