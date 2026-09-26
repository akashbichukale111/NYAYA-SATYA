"""UNWIND Core governance adapter for NYAYA-SATYA Auto-Healer.

Ensures that all repair proposals are routed strictly through UNWIND governance
state machine to the Human Legal Gate. Prohibits autonomous execution.
"""

from __future__ import annotations

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from unwind_core.gate.human_gate import HumanLegalGate
from unwind_core.governance.state_machine import GovernanceStateMachine


class AutomatedRepairExecutionProhibitedError(PermissionError):
    """Raised when an automated system attempts to execute a repair without human approval."""


class UnwindRepairAdapter:
    """Routes repair proposals through UNWIND governance to the Human Legal Gate."""

    def __init__(
        self,
        state_machine: GovernanceStateMachine | None = None,
        human_gate: HumanLegalGate | None = None,
    ) -> None:
        self._sm = state_machine or GovernanceStateMachine()
        self._gate = human_gate

    def route_for_governance_review(
        self, proposal: ReasoningProposal
    ) -> ProposalStatus:
        """Advance proposal: PROPOSED -> GOVERNANCE_REVIEW -> ASK_HUMAN."""
        self._sm.transition(
            proposal,
            ProposalStatus.GOVERNANCE_REVIEW,
            actor_type="SYSTEM",
            actor_id="nyaya_repair_engine",
            reason="Repair proposal submitted for governance verification",
        )
        self._sm.transition(
            proposal,
            ProposalStatus.ASK_HUMAN,
            actor_type="SYSTEM",
            actor_id="nyaya_repair_engine",
            reason="Consequential case repair requires human jurist gate approval",
        )
        return proposal.status

    def assert_human_approved(self, proposal: ReasoningProposal) -> None:
        """Enforce that consequential repairs cannot execute without HUMAN_APPROVED status."""
        if proposal.status != ProposalStatus.HUMAN_APPROVED:
            raise AutomatedRepairExecutionProhibitedError(
                f"Cannot execute repair proposal '{proposal.proposal_id}' in status '{proposal.status.value}'. "
                "Final authority requires Human Legal Gate decision (HUMAN_APPROVED)."
            )
