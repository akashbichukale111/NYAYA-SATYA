"""Should-Not-Change analysis for NYAYA-SATYA.

Verifies that irrelevant perturbations do not affect critical case state.
Flags UNEXPECTED_PROPAGATION when unrelated changes propagate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.intervention import Intervention
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


@dataclass
class ShouldNotChangeResult:
    """Result of should-not-change analysis."""

    intervention_id: str
    protected_nodes: list[str]
    unexpected_changes: list[str] = field(default_factory=list)
    status: str = "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "protected_nodes": self.protected_nodes,
            "unexpected_changes": self.unexpected_changes,
            "status": self.status,
        }


class ShouldNotChangeAnalyzer:
    """Verifies that irrelevant perturbations do not affect protected nodes."""

    def __init__(self) -> None:
        self._blast_engine = BlastRadiusEngine()

    def analyze(
        self,
        twin: CaseDigitalTwin,
        intervention: Intervention,
        protected_node_ids: list[str],
    ) -> ShouldNotChangeResult:
        """Run intervention and verify protected nodes are unchanged."""
        report = self._blast_engine.compute(twin, intervention)

        affected = set(
            [e.node_id for e in report.direct_effects]
            + [e.node_id for e in report.indirect_effects]
        )

        unexpected = [nid for nid in protected_node_ids if nid in affected]

        return ShouldNotChangeResult(
            intervention_id=intervention.intervention_id,
            protected_nodes=protected_node_ids,
            unexpected_changes=unexpected,
            status="UNEXPECTED_PROPAGATION" if unexpected else "PASS",
        )
