"""Adversarial adapter for NYAYA-SATYA Auto-Healer.

Connects Phase 4 Adversarial Gauntlet reports to Phase 6 repair candidate generation.
"""

from __future__ import annotations

from typing import Any

from nyaya_adversarial.contracts.result import AdversarialFinding, AdversarialGauntletReport
from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.engine.repair_generator import RepairGenerator
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class AdversarialRepairAdapter:
    """Adapts adversarial gauntlet findings into actionable repair proposals."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self._generator = RepairGenerator(twin)

    def extract_repairs_from_gauntlet(
        self,
        report: AdversarialGauntletReport,
    ) -> list[RepairCandidate]:
        """Convert all findings from a gauntlet report into repair candidates."""
        return self._generator.generate_all_repairs(report.findings)

    def extract_repairs_from_findings(
        self,
        findings: list[AdversarialFinding],
    ) -> list[RepairCandidate]:
        """Convert a list of adversarial findings into repair candidates."""
        return self._generator.generate_all_repairs(findings)
