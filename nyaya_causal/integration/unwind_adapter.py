"""UNWIND governance adapter for NYAYA-SATYA Causal Reasoning.

Ensures all causal and counterfactual findings pass through
governance review and Human Legal Gate before any consequential action.
"""

from __future__ import annotations

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from unwind_core.governance.state_machine import GovernanceStateMachine


class CausalUnwindAdapter:
    """Routes causal proposals through UNWIND governance."""

    def __init__(self, state_machine: GovernanceStateMachine | None = None) -> None:
        self._sm = state_machine or GovernanceStateMachine()

    def submit_for_review(self, proposal: ReasoningProposal) -> ProposalStatus:
        """Submit a causal proposal for governance review."""
        # PROPOSED -> GOVERNANCE_REVIEW
        self._sm.transition(
            proposal,
            ProposalStatus.GOVERNANCE_REVIEW,
            actor_type="SYSTEM",
            actor_id="causal_reasoning_engine",
            reason="Causal analysis proposal submitted for governance review",
        )
        # GOVERNANCE_REVIEW -> ASK_HUMAN
        self._sm.transition(
            proposal,
            ProposalStatus.ASK_HUMAN,
            actor_type="SYSTEM",
            actor_id="causal_reasoning_engine",
            reason="Causal analysis requires human legal gate review",
        )
        return proposal.status
