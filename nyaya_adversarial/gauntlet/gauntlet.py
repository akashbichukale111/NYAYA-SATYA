"""Adversarial Gauntlet Master Orchestrator for NYAYA-SATYA.

Coordinates attack generation, isolated simulation execution, and findings compilation.
Strictly verifies that the canonical CaseDigitalTwin hash remains completely unmodified.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_adversarial.contracts.assumption import AssumptionRegistry
from nyaya_adversarial.contracts.attack import AttackScenario
from nyaya_adversarial.contracts.result import (
    AdversarialFinding,
    AdversarialGauntletReport,
)
from nyaya_adversarial.gauntlet.attack_evaluator import AttackEvaluator
from nyaya_adversarial.gauntlet.attack_executor import AttackExecutor
from nyaya_adversarial.gauntlet.attack_generators import AttackGeneratorSuite
from nyaya_twin.contracts.case_twin import CaseDigitalTwin, compute_twin_hash


class AdversarialGauntlet:
    """Master orchestrator running the 10-class attack gauntlet against a case."""

    def __init__(
        self,
        twin: CaseDigitalTwin,
        assumption_registry: AssumptionRegistry | None = None,
    ) -> None:
        self.twin = twin
        self.case_id = twin.case_id
        self.assumptions = assumption_registry or AssumptionRegistry(case_id=twin.case_id)
        self.generator = AttackGeneratorSuite(twin, self.assumptions)
        self.executor = AttackExecutor(twin)
        self.evaluator = AttackEvaluator()

    def run_gauntlet(
        self,
        attack_scenarios: list[AttackScenario] | None = None,
    ) -> AdversarialGauntletReport:
        """Runs the adversarial gauntlet and returns a comprehensive stress report."""
        # 1. Snapshot initial hash to verify immutability
        initial_hash = compute_twin_hash(self.twin)

        # 2. Generate attacks if not explicitly provided
        scenarios = attack_scenarios or self.generator.generate_all_attacks()

        # 3. Execute and evaluate each attack
        findings: list[AdversarialFinding] = []
        for scenario in scenarios:
            obs = self.executor.execute(scenario)
            finding = self.evaluator.evaluate(scenario, obs)
            if finding:
                findings.append(finding)

        # 4. Strict Immutability Verification: Ensure twin state did not drift
        final_hash = compute_twin_hash(self.twin)
        if initial_hash != final_hash:
            raise RuntimeError(
                f"IMMUTABILITY VIOLATION: CaseDigitalTwin state mutated during adversarial gauntlet! "
                f"Initial={initial_hash}, Final={final_hash}"
            )

        report_id = f"gauntlet_{self.case_id}_{uuid.uuid4().hex[:8]}"
        return AdversarialGauntletReport(
            report_id=report_id,
            case_id=self.case_id,
            twin_hash=final_hash,
            findings=findings,
            total_attacks_executed=len(scenarios),
            status="AWAITING_LEGAL_GATE",
        )
