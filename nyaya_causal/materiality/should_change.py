"""Should-Change analysis for NYAYA-SATYA.

Verifies that materially relevant inputs produce expected dependent state changes.
Flags EXPECTED_CHANGE_MISSING when expected effects do not propagate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_causal.contracts.intervention import Intervention
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


@dataclass
class ShouldChangeResult:
    """Result of should-change analysis."""

    intervention_id: str
    expected_changes: list[str]
    actual_changes: list[str]
    missing_changes: list[str] = field(default_factory=list)
    status: str = "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "expected_changes": self.expected_changes,
            "actual_changes": self.actual_changes,
            "missing_changes": self.missing_changes,
            "status": self.status,
        }


class ShouldChangeAnalyzer:
    """Verifies that material interventions produce expected state changes."""

    def __init__(self) -> None:
        self._blast_engine = BlastRadiusEngine()

    def analyze(
        self,
        twin: CaseDigitalTwin,
        intervention: Intervention,
        expected_changed_ids: list[str],
    ) -> ShouldChangeResult:
        """Run intervention and verify expected changes occurred."""
        report = self._blast_engine.compute(twin, intervention)

        actual_changes = set(
            [e.node_id for e in report.direct_effects]
            + [e.node_id for e in report.indirect_effects]
        )

        missing = [nid for nid in expected_changed_ids if nid not in actual_changes]

        return ShouldChangeResult(
            intervention_id=intervention.intervention_id,
            expected_changes=expected_changed_ids,
            actual_changes=sorted(actual_changes),
            missing_changes=missing,
            status="EXPECTED_CHANGE_MISSING" if missing else "PASS",
        )
