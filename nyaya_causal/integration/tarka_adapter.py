"""TARKA-VYUH adapter for NYAYA-SATYA Causal Reasoning.

Formats causal analysis outputs as ReasoningProposal contracts for governance.
Supports CAUSAL_ANALYSIS and COUNTERFACTUAL reasoning types.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_causal.contracts.scenario import CounterfactualScenario
from nyaya_causal.provenance.causal_provenance import CausalProvenanceTracker
from tarka_vyuh.contracts.proposal import (
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef


class CausalTarkaAdapter:
    """Formats causal findings as TARKA-VYUH ReasoningProposal contracts."""

    def blast_radius_to_proposal(
        self,
        report: BlastRadiusReport,
        *,
        evidence_ids: list[str],
    ) -> ReasoningProposal:
        """Convert a blast-radius report to a ReasoningProposal."""
        prov = CausalProvenanceTracker.create_blast_radius_provenance(
            report_id=report.report_id,
            scenario_hash=report.scenario_hash,
        )

        claims = [
            f"Intervention on {report.target_type} {report.target_id}: {report.intervention_summary}",
            f"Direct effects: {len(report.direct_effects)} nodes affected",
            f"Indirect effects: {len(report.indirect_effects)} nodes affected",
            f"Unaffected nodes: {len(report.unaffected_nodes)}",
        ]

        assumptions = []
        if report.broken_dependencies:
            assumptions.append(f"{len(report.broken_dependencies)} dependencies broken")

        return ReasoningProposal(
            proposal_id=f"PROP_CR_{uuid.uuid4().hex[:12]}",
            case_id=report.case_id,
            reasoning_type=ReasoningType.CAUSAL_ANALYSIS,
            input_evidence_ids=evidence_ids if evidence_ids else [report.target_id],
            claims=claims,
            assumptions=assumptions,
            uncertainty=0.4,
            proposed_action=ProposedAction(
                action_type="CAUSAL_BLAST_RADIUS_REVIEW",
                target_id=report.target_id,
                parameters={"report_id": report.report_id},
                is_consequential=False,
            ),
            provenance_refs=[prov],
        )

    def scenario_to_proposal(
        self,
        scenario: CounterfactualScenario,
        *,
        evidence_ids: list[str],
    ) -> ReasoningProposal:
        """Convert a counterfactual scenario to a ReasoningProposal."""
        prov = CausalProvenanceTracker.create_scenario_provenance(
            scenario_id=scenario.scenario_id,
            case_id=scenario.case_id,
            scenario_hash=scenario.integrity_hash,
        )

        claims = [
            f"Counterfactual scenario {scenario.scenario_id}: {scenario.intervention.operation.value} on {scenario.intervention.target_id}",
            f"Status: {scenario.status.value}",
        ]
        if scenario.blast_radius:
            claims.append(
                f"Blast radius: {len(scenario.blast_radius.direct_effects)} direct, "
                f"{len(scenario.blast_radius.indirect_effects)} indirect effects"
            )

        return ReasoningProposal(
            proposal_id=f"PROP_CF_{uuid.uuid4().hex[:12]}",
            case_id=scenario.case_id,
            reasoning_type=ReasoningType.COUNTERFACTUAL,
            input_evidence_ids=evidence_ids if evidence_ids else [scenario.intervention.target_id],
            claims=claims,
            assumptions=list(scenario.assumptions),
            uncertainty=0.5,
            proposed_action=ProposedAction(
                action_type="COUNTERFACTUAL_SCENARIO_REVIEW",
                target_id=scenario.scenario_id,
                parameters={"scenario_id": scenario.scenario_id},
                is_consequential=False,
            ),
            provenance_refs=[prov],
        )
