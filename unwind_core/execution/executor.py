"""Governed Execution Engine for UNWIND Core.

Performs consequential execution ONLY after verification by the ExecutionGuard
and state transition to EXECUTED.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from unwind_core.execution.guard import ExecutionBlockedError, ExecutionGuard
from unwind_core.gate.human_gate import HumanDecisionRecord
from unwind_core.governance.audit import AuditEventType, AuditStore, get_audit_store
from unwind_core.governance.state_machine import GovernanceStateMachine


class GovernedExecutor:
    """Safely executes human-approved reasoning proposals."""

    def __init__(
        self,
        guard: ExecutionGuard | None = None,
        state_machine: GovernanceStateMachine | None = None,
        audit_store: AuditStore | None = None,
    ) -> None:
        self.guard = guard or ExecutionGuard()
        self.state_machine = state_machine or GovernanceStateMachine()
        self.audit_store = audit_store or get_audit_store()
        self._handlers: dict[str, Callable[[ReasoningProposal], dict[str, Any]]] = {}

    def register_action_handler(
        self,
        action_type: str,
        handler: Callable[[ReasoningProposal], dict[str, Any]],
    ) -> None:
        self._handlers[action_type] = handler

    def execute(
        self,
        proposal: ReasoningProposal,
        decision_record: HumanDecisionRecord | None,
        *,
        actor_id: str,
    ) -> dict[str, Any]:
        """Verifies preconditions, executes registered handler, and transitions state to EXECUTED."""
        # 1. Log execution attempt in audit
        self.audit_store.record_event(
            proposal_id=proposal.proposal_id,
            case_id=proposal.case_id,
            event_type=AuditEventType.EXECUTION_ATTEMPTED,
            previous_status=proposal.status,
            new_status=proposal.status,
            actor_type="SYSTEM",
            actor_id=actor_id,
            proposal_hash=proposal.compute_hash(),
            provenance_refs=[p.ref_id for p in proposal.provenance_refs],
            reason="Consequential execution initiated",
        )

        # 2. Strict safety verification
        self.guard.verify(
            proposal=proposal,
            decision_record=decision_record,
            actor_id=actor_id,
        )

        # 3. Dispatch action handler
        action_type = proposal.proposed_action.action_type
        handler = self._handlers.get(action_type)

        execution_id = f"exec_{uuid.uuid4().hex[:16]}"
        timestamp = datetime.now(UTC)

        if handler is not None:
            handler_result = handler(proposal)
        else:
            # Default governed execution receipt
            handler_result = {
                "action": action_type,
                "target_id": proposal.proposed_action.target_id,
                "parameters": proposal.proposed_action.parameters,
                "dispatched": True,
            }

        receipt = {
            "execution_id": execution_id,
            "proposal_id": proposal.proposal_id,
            "executed_at": timestamp.isoformat(),
            "executor_actor": actor_id,
            "handler_result": handler_result,
            "status": "SUCCESS",
        }

        # 4. State transition to EXECUTED
        self.state_machine.transition(
            proposal,
            ProposalStatus.EXECUTED,
            actor_type="SYSTEM",
            actor_id=actor_id,
            reason=f"Consequential action {action_type} successfully executed. Receipt: {execution_id}",
        )

        # 5. Mark executed in guard for idempotency
        self.guard.mark_executed(proposal, receipt)

        return receipt


__all__ = [
    "GovernedExecutor",
]
