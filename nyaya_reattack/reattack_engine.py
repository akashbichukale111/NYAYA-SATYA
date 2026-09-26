"""Re-attack execution engine for NYAYA-SATYA.

Runs independent re-attack scenarios against the post-repair digital twin.
"""

from __future__ import annotations

from typing import Any

from nyaya_adversarial.contracts.attack import AttackScenario
from nyaya_adversarial.contracts.result import AdversarialFinding, AdversarialGauntletReport
from nyaya_adversarial.gauntlet.gauntlet import AdversarialGauntlet
from nyaya_reattack.independent_attacker import IndependentAttacker
from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class ReAttackEngine:
    """Coordinates execution of independent re-attack suites against repaired twins."""

    def __init__(self, attacker: IndependentAttacker | None = None) -> None:
        self.attacker = attacker or IndependentAttacker()

    def execute_reattack(
        self,
        repaired_twin: CaseDigitalTwin,
        repair: RepairCandidate,
        *,
        custom_scenarios: list[AttackScenario] | None = None,
    ) -> AdversarialGauntletReport:
        """Run re-attack scenarios against the repaired twin simulation."""
        scenarios = custom_scenarios or self.attacker.generate_reattacks(repaired_twin, repair)

        gauntlet = AdversarialGauntlet(repaired_twin)
        report = gauntlet.run_gauntlet(attack_scenarios=scenarios)
        return report
