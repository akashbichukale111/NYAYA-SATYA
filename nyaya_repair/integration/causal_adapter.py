"""Causal reasoning adapter for NYAYA-SATYA Auto-Healer.

Recalculates blast-radius and causal graph consequences following repair simulation.
"""

from __future__ import annotations

from typing import Any

from nyaya_causal.blast_radius.engine import BlastRadiusEngine
from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_causal.contracts.intervention import (
    Intervention,
    InterventionOperation,
    InterventionTargetType,
)
from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class CausalRepairAdapter:
    """Computes blast-radius and causal impact of repair candidates."""

    def __init__(self) -> None:
        self._blast_engine = BlastRadiusEngine()

    def recalculate_blast_radius(
        self,
        twin_before: CaseDigitalTwin,
        repair: RepairCandidate,
    ) -> BlastRadiusReport:
        """Measure downstream impact of applying the repair as an intervention."""
        # Map repair candidate to a causal intervention
        target_id = repair.target_claim_id or repair.target_vulnerability_id
        target_type = InterventionTargetType.CLAIM if repair.target_claim_id else InterventionTargetType.EVIDENCE

        intervention = Intervention(
            intervention_id=f"INT_REP_{repair.repair_id}",
            case_id=repair.case_id,
            target_id=target_id,
            target_type=target_type,
            operation=InterventionOperation.CHANGE_VALUE,
            rationale=repair.rationale,
            hypothetical_state=repair.proposed_change,
        )

        return self._blast_engine.compute(twin_before, intervention)
