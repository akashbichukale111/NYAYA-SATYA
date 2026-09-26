"""TARKA-VYUH adapter for NYAYA-SATYA Auto-Healer.

Translates repair proposals into typed ReasoningProposal contracts for UNWIND governance.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.provenance.repair_provenance import RepairProvenanceTracker
from tarka_vyuh.contracts.proposal import (
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)


class TarkaRepairAdapter:
    """Formats repair candidates into TARKA-VYUH ReasoningProposal objects."""

    def repair_to_proposal(
        self,
        repair: RepairCandidate,
    ) -> ReasoningProposal:
        """Convert a RepairCandidate into a ReasoningProposal."""
        prov = RepairProvenanceTracker.create_repair_provenance(repair)

        claims = [
            f"Repair candidate {repair.repair_id}: {repair.change_type.value}",
            f"Target vulnerability: {repair.target_vulnerability_id}",
            f"Rationale: {repair.rationale}",
        ]
        if repair.expected_effects:
            claims.append(f"Expected effects: {'; '.join(repair.expected_effects)}")

        assumptions = [
            "Repair operates as a non-adjudicative draft improvement.",
            "Requires human legal gate confirmation before any court filing.",
        ]

        action = ProposedAction(
            action_type="APPLY_CASE_REPAIR",
            target_id=repair.repair_id,
            parameters={
                "change_type": repair.change_type.value,
                "target_vulnerability_id": repair.target_vulnerability_id,
                "proposed_change": repair.proposed_change,
            },
            is_consequential=True,
        )

        return ReasoningProposal(
            proposal_id=f"PROP_REP_{uuid.uuid4().hex[:12]}",
            case_id=repair.case_id,
            reasoning_type=ReasoningType.REPAIR_PROPOSAL,
            input_evidence_ids=repair.evidence_refs if repair.evidence_refs else [repair.target_vulnerability_id],
            claims=claims,
            assumptions=assumptions,
            uncertainty=0.35,
            proposed_action=action,
            provenance_refs=[prov],
        )
