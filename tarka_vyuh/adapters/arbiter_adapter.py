"""Safe Arbiter Adapter for TARKA-VYUH.

Wraps the legacy court/arbiter.py NeutralArbiter to enforce the governance boundary:
The arbiter's output becomes an analytical ReasoningProposal, NEVER an autonomous execution.
Even when exposure is below the legacy threshold ($50,000), it must flow through
UNWIND Governance and the Human Legal Gate.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from court.arbiter import ArbiterOutcome, NeutralArbiter
from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class SafeArbiterAdapter:
    """Adapts court rulings into governed TARKA-VYUH proposals."""

    def __init__(self, arbiter: NeutralArbiter | None = None) -> None:
        self.arbiter = arbiter or NeutralArbiter()

    def rule_and_propose(
        self,
        *,
        case_id: str,
        notice: Any,
        pleas: list[Any],
        challenges: list[Any],
        owner_ids: list[str],
        model: Any,
        now: datetime | None = None,
        total_exposure_minor: int = 0,
        converged: bool = True,
        assessor: str | None = None,
        rederiver: str | None = None,
        provenance_refs: list[ProvenanceRef] | None = None,
    ) -> ReasoningProposal:
        """Runs the arbiter to weigh arguments, then encapsulates the outcome into a proposal.

        CRITICAL SAFETY GUARANTEE:
        Legacy NeutralArbiter considered rulings with total_exposure_minor < 5,000,000
        as self-executing (advisory=False).
        This adapter ALWAYS emits a ProposalStatus.PROPOSED proposal.
        Autonomous execution is structurally disabled.
        """
        current_time = now or datetime.now(UTC)

        outcome: ArbiterOutcome = self.arbiter.rule(
            notice=notice,
            pleas=pleas,
            challenges=challenges,
            owner_ids=owner_ids,
            model=model,
            now=current_time,
            total_exposure_minor=total_exposure_minor,
            converged=converged,
            assessor=assessor,
            rederiver=rederiver,
        )

        return self.adapt_outcome(
            case_id=case_id,
            outcome=outcome,
            pleas=pleas,
            now=current_time,
            provenance_refs=provenance_refs,
        )

    def adapt_outcome(
        self,
        *,
        case_id: str,
        outcome: ArbiterOutcome,
        pleas: list[Any] | None = None,
        now: datetime | None = None,
        provenance_refs: list[ProvenanceRef] | None = None,
    ) -> ReasoningProposal:
        """Transforms an existing ArbiterOutcome into a ReasoningProposal."""
        current_time = now or datetime.now(UTC)

        # Assemble claims from ruling and dissent
        claims = [f"Decision: {outcome.ruling.decision}"]
        if outcome.ruling.rationale:
            claims.append(f"Rationale: {outcome.ruling.rationale}")
        for d in outcome.dissent:
            claims.append(f"Dissent: {d}")

        # Assemble input evidence and provenance
        resolved_provs: list[ProvenanceRef] = list(provenance_refs or [])
        evidence_ids: list[str] = []

        if pleas:
            for p in pleas:
                cid = getattr(p, "conclusion_id", "unknown_conclusion")
                evidence_ids.append(cid)
                for ev in getattr(p, "evidence", []):
                    evidence_ids.append(str(ev))

        if not resolved_provs:
            # Generate baseline provenance record for the hearing
            hearing_summary = {
                "case_id": case_id,
                "arbiter_id": outcome.ruling.arbiter_id,
                "decision": outcome.ruling.decision,
                "conceded": outcome.conceded,
            }
            resolved_provs.append(
                ProvenanceRef.create(
                    source_id=outcome.ruling.arbiter_id,
                    source_type="ARBITER_HEARING",
                    evidence_id=f"hearing_{case_id}",
                    content=hearing_summary,
                )
            )

        if not evidence_ids:
            evidence_ids = [p.evidence_id for p in resolved_provs]

        # Uncertainty: higher if not converged or if dissent exists
        uncertainty = 0.05
        if not outcome.ruling.converged:
            uncertainty = 0.60
        elif outcome.dissent:
            uncertainty = min(0.40, 0.05 + 0.05 * len(outcome.dissent))

        # Proposed action captures the allocation without executing it
        proposed_action = ProposedAction(
            action_type="SETTLE_REPAIR",
            target_id=case_id,
            parameters={
                "preserved": outcome.preserved,
                "amended": outcome.amended,
                "conceded": outcome.conceded,
                "conceded_conclusion_ids": outcome.ruling.conceded_conclusion_ids,
                "legacy_advisory": outcome.ruling.advisory,
                "arbiter_id": outcome.ruling.arbiter_id,
                "converged": outcome.ruling.converged,
            },
            is_consequential=True,
        )

        proposal = ReasoningProposal(
            proposal_id=f"prop_arb_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            reasoning_type=ReasoningType.REPAIR_PROPOSAL,
            input_evidence_ids=evidence_ids,
            claims=claims,
            assumptions=[
                "Contested resources allocated by arithmetic claim weight",
                "Unevidenced pleas discounted to 0.4 weight",
            ],
            uncertainty=uncertainty,
            proposed_action=proposed_action,
            provenance_refs=resolved_provs,
            generated_at=current_time,
            model_metadata={
                "arbiter_id": outcome.ruling.arbiter_id,
                "legacy_advisory_flag": outcome.ruling.advisory,
            },
            status=ProposalStatus.PROPOSED,
        )
        return proposal


__all__ = [
    "SafeArbiterAdapter",
]
