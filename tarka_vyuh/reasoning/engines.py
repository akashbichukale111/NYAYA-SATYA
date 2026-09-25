"""Reasoning Engines for TARKA-VYUH.

Contains real proposal generator engines for implemented capabilities.
Unbuilt capabilities raise ReasoningEngineNotImplementedError.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from tarka_vyuh.contracts.proposal import (
    ProposalStatus,
    ProposedAction,
    ReasoningProposal,
    ReasoningType,
)
from tarka_vyuh.contracts.provenance import ProvenanceRef
from tarka_vyuh.reasoning.registry import (
    CapabilityStatus,
    ReasoningEngineNotImplementedError,
    register_capability,
)


class AdversarialChallengeEngine:
    """Generates an adversarial challenge proposal against a claim.

    Does NOT decide the outcome. Generates an analytical proposal for human review.
    """

    def __call__(
        self,
        *,
        case_id: str,
        target_id: str,
        claims: list[str],
        provenance_refs: list[ProvenanceRef],
        assumptions: list[str] | None = None,
        uncertainty: float = 0.25,
        action_parameters: dict[str, Any] | None = None,
        model_metadata: dict[str, Any] | None = None,
    ) -> ReasoningProposal:
        if not claims:
            raise ValueError("Adversarial challenge requires at least one claim")
        if not provenance_refs:
            raise ValueError("Adversarial challenge requires provenance references")

        evidence_ids = [p.evidence_id for p in provenance_refs]
        action = ProposedAction(
            action_type="CHALLENGE_PREMISE",
            target_id=target_id,
            parameters=action_parameters or {"challenge_basis": "adversarial_stress_test"},
            is_consequential=True,
        )

        proposal = ReasoningProposal(
            proposal_id=f"prop_adv_{uuid.uuid4().hex[:12]}",
            case_id=case_id,
            reasoning_type=ReasoningType.ADVERSARIAL_CHALLENGE,
            input_evidence_ids=evidence_ids,
            claims=claims,
            assumptions=assumptions or ["Standard evidentiary burden applies"],
            uncertainty=uncertainty,
            proposed_action=action,
            provenance_refs=provenance_refs,
            generated_at=datetime.now(UTC),
            model_metadata=model_metadata or {"engine": "AdversarialChallengeEngine@1.0.0"},
            status=ProposalStatus.PROPOSED,
        )
        return proposal


# Wire the engine into the registry
register_capability(
    ReasoningType.ADVERSARIAL_CHALLENGE,
    CapabilityStatus.IMPLEMENTED,
    "Generates adversarial stress-testing challenge against presented claims",
    engine_factory=lambda: AdversarialChallengeEngine(),
)

__all__ = [
    "AdversarialChallengeEngine",
]
