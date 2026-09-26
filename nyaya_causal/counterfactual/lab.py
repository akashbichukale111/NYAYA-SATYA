"""Counterfactual Lab for NYAYA-SATYA.

Central coordinator for counterfactual scenario lifecycle:
- CREATE, VALIDATE, RUN, COMPARE, EXPORT, REPLAY.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from nyaya_causal.contracts.intervention import Intervention
from nyaya_causal.contracts.scenario import CounterfactualScenario, ScenarioStatus
from nyaya_causal.counterfactual.scenario_runner import ScenarioRunner
from nyaya_twin.contracts.case_twin import CaseDigitalTwin

MAX_INTERVENTIONS_PER_SCENARIO = 10
MAX_SCENARIO_NODES = 1000


class CounterfactualLab:
    """Central counterfactual scenario management."""

    def __init__(self) -> None:
        self._scenarios: dict[str, CounterfactualScenario] = {}
        self._runner = ScenarioRunner()

    def create_scenario(
        self,
        *,
        case_id: str,
        intervention: Intervention,
        base_twin_version: int,
        preconditions: list[str] | None = None,
        assumptions: list[str] | None = None,
        execution_config: dict[str, Any] | None = None,
    ) -> CounterfactualScenario:
        """Create a new counterfactual scenario."""
        scenario_id = f"SCN_{uuid.uuid4().hex[:12]}"
        scenario = CounterfactualScenario(
            scenario_id=scenario_id,
            case_id=case_id,
            base_twin_version=base_twin_version,
            intervention=intervention,
            preconditions=preconditions or [],
            assumptions=assumptions or [],
            execution_config=execution_config or {},
        )
        self._scenarios[scenario_id] = scenario
        return scenario

    def validate_scenario(self, scenario_id: str) -> tuple[bool, list[str]]:
        """Validate a scenario before execution."""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return False, [f"Scenario {scenario_id} not found"]

        errors: list[str] = []
        if not scenario.intervention.target_id:
            errors.append("Intervention must specify a target_id")
        if not scenario.case_id:
            errors.append("Scenario must specify a case_id")
        if scenario.intervention.case_id != scenario.case_id:
            errors.append("Intervention case_id must match scenario case_id")

        if not errors:
            scenario.status = ScenarioStatus.VALIDATED
        return len(errors) == 0, errors

    def run_scenario(
        self, scenario_id: str, twin: CaseDigitalTwin
    ) -> CounterfactualScenario:
        """Execute a validated scenario against the twin."""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ValueError(f"Scenario {scenario_id} not found")

        if scenario.status not in (ScenarioStatus.CREATED, ScenarioStatus.VALIDATED):
            raise ValueError(f"Scenario {scenario_id} is in status {scenario.status.value}, cannot run")

        result = self._runner.run(scenario, twin)
        self._scenarios[scenario_id] = result
        return result

    def replay_scenario(
        self, scenario_id: str, twin: CaseDigitalTwin
    ) -> CounterfactualScenario:
        """Re-run an existing scenario for reproducibility verification."""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Reset status for replay
        scenario.status = ScenarioStatus.VALIDATED
        scenario.blast_radius = None
        scenario.comparison = None
        scenario.completed_at = None
        scenario.error_message = ""

        return self._runner.run(scenario, twin)

    def get_scenario(self, scenario_id: str) -> CounterfactualScenario | None:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self, case_id: str | None = None) -> list[CounterfactualScenario]:
        if case_id:
            return [s for s in self._scenarios.values() if s.case_id == case_id]
        return list(self._scenarios.values())

    def export_scenario(self, scenario_id: str) -> dict[str, Any]:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ValueError(f"Scenario {scenario_id} not found")
        return scenario.to_dict()

    def reset_for_test(self) -> None:
        """Test hook to clear all scenarios."""
        self._scenarios.clear()
