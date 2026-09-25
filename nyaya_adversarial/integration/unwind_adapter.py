"""UNWIND Core Governance Adapter for NYAYA-SATYA Adversarial Subsystem.

Ensures all adversarial proposals conform to UNWIND Core governance policies
and must pass through the Human Legal Gate before any execution.
"""

from __future__ import annotations

from typing import Any

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from unwind_core.gate.human_gate import (
    AutomatedApprovalProhibitedError,
    HumanDecisionRecord,
    HumanDecisionType,
    HumanLegalGate,
)
from unwind_core.governance.state_machine import GovernanceStateMachine


class UnwindAdversarialAdapter:
    """Governance boundary interface between Adversarial Subsystem and UNWIND Core."""

    def __init__(
        self,
        state_machine: GovernanceStateMachine | None = None,
        human_gate: HumanLegalGate | None = None,
    ) -> None:
        self.state_machine = state_machine or GovernanceStateMachine()
        self.human_gate = human_gate or HumanLegalGate(state_machine=self.state_machine)

    def route_to_human_gate(self, proposal: ReasoningProposal) -> ReasoningProposal:
        """Transitions proposal through governance review to ASK_HUMAN."""
        if proposal.status == ProposalStatus.PROPOSED:
            self.state_machine.transition(
                proposal,
                ProposalStatus.GOVERNANCE_REVIEW,
                actor_type="SYSTEM",
                actor_id="tarka-adversarial-gauntlet",
                reason="Adversarial finding routed to governance review",
            )
        if proposal.status == ProposalStatus.GOVERNANCE_REVIEW:
            self.state_machine.transition(
                proposal,
                ProposalStatus.ASK_HUMAN,
                actor_type="SYSTEM",
                actor_id="unwind-governance-engine",
                reason="Escalating consequential finding to Human Legal Gate",
            )
        return proposal

    def record_human_gate_decision(
        self,
        proposal: ReasoningProposal,
        decision_record: HumanDecisionRecord,
    ) -> ReasoningProposal:
        """Processes a human decision record through the Human Legal Gate."""
        return self.human_gate.record_decision(proposal, decision_record)

    def assert_no_automated_execution(self, proposal: ReasoningProposal) -> None:
        """Verifies that an unapproved or automated proposal cannot be executed."""
        if proposal.status != ProposalStatus.HUMAN_APPROVED:
            raise AutomatedApprovalProhibitedError(
                f"Adversarial proposal {proposal.proposal_id} cannot be executed without human approval. "
                f"Current status: {proposal.status.value}"
            )
