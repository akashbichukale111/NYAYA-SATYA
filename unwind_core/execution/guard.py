"""Execution Guard for UNWIND Core.

The deterministic boundary ensuring that NO consequential action can execute without
verified human approval, provenance integrity, and state consistency.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from tarka_vyuh.validation.validator import validate_proposal
from unwind_core.gate.human_gate import HumanDecisionRecord, HumanDecisionType
from unwind_core.governance.audit import AuditEventType, AuditStore, get_audit_store


class ExecutionBlockedError(RuntimeError):
    """Raised when the ExecutionGuard rejects an execution attempt."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Execution blocked by safety guard: {reason}")


@dataclass(frozen=True)
class ExecutionVerification:
    allowed: bool
    proposal_id: str
    decision_record: HumanDecisionRecord | None
    reason: str


class ExecutionGuard:
    """Deterministic safety guard verifying preconditions before consequential execution."""

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        self.audit_store = audit_store or get_audit_store()
        self._lock = threading.Lock()
        self._executed_proposals: dict[str, dict[str, Any]] = {}

    def verify(
        self,
        proposal: ReasoningProposal,
        decision_record: HumanDecisionRecord | None,
        *,
        actor_id: str,
        actor_type: str = "SYSTEM",
    ) -> ExecutionVerification:
        """Verifies all safety criteria. Raises ExecutionBlockedError on failure."""
        with self._lock:
            # 1. Structural validity & provenance presence check
            violations = validate_proposal(proposal)
            if violations:
                self._record_blocked(proposal, actor_id, f"Malformed proposal: {'; '.join(violations)}")
                raise ExecutionBlockedError(f"Malformed proposal: {'; '.join(violations)}")

            # 2. Check current proposal status
            if proposal.status is not ProposalStatus.HUMAN_APPROVED:
                reason = f"Proposal status is {proposal.status.value}, expected HUMAN_APPROVED."
                if proposal.status is ProposalStatus.PROPOSED:
                    reason += " AI reasoning proposals cannot execute directly."
                elif proposal.status is ProposalStatus.ASK_HUMAN:
                    reason += " Proposal is awaiting human decision."
                elif proposal.status is ProposalStatus.REJECTED:
                    reason += " Proposal was rejected by human legal authority."
                elif proposal.status is ProposalStatus.EXECUTED:
                    reason += " Proposal was already executed."

                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            # 3. Check for human approval record
            if decision_record is None:
                reason = "Missing human decision record. Consequential actions require explicit human approval."
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            if decision_record.decision is not HumanDecisionType.APPROVE:
                reason = f"Human decision is {decision_record.decision.value}, cannot execute."
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            if decision_record.proposal_id != proposal.proposal_id:
                reason = f"Human decision proposal_id mismatch ({decision_record.proposal_id} != {proposal.proposal_id})."
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            # 4. Proposal Integrity Check (Anti-Tampering)
            current_hash = proposal.compute_hash()
            if current_hash != decision_record.proposal_version_hash:
                reason = (
                    f"Approved proposal has changed! Hash at approval ({decision_record.proposal_version_hash[:12]}...) "
                    f"does not match current hash ({current_hash[:12]}...). Potential post-approval tampering detected."
                )
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            # 5. Provenance check
            if not proposal.provenance_refs:
                reason = "Proposal contains zero provenance references. Execution blocked."
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            # 6. Idempotency / Double-Execution Check
            if proposal.proposal_id in self._executed_proposals:
                reason = f"Proposal {proposal.proposal_id} has already been executed. Duplicate execution prevented."
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            # 7. Authorized Actor check
            if not actor_id or not actor_id.strip():
                reason = "Executor actor_id is required."
                self._record_blocked(proposal, actor_id, reason)
                raise ExecutionBlockedError(reason)

            return ExecutionVerification(
                allowed=True,
                proposal_id=proposal.proposal_id,
                decision_record=decision_record,
                reason="All governance and integrity gates passed.",
            )

    def mark_executed(
        self,
        proposal: ReasoningProposal,
        execution_receipt: dict[str, Any],
    ) -> None:
        """Records successful execution in the idempotency registry."""
        with self._lock:
            self._executed_proposals[proposal.proposal_id] = execution_receipt

    def get_execution_receipt(self, proposal_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._executed_proposals.get(proposal_id)

    def _record_blocked(self, proposal: ReasoningProposal, actor_id: str, reason: str) -> None:
        self.audit_store.record_event(
            proposal_id=proposal.proposal_id,
            case_id=proposal.case_id,
            event_type=AuditEventType.EXECUTION_BLOCKED,
            previous_status=proposal.status,
            new_status=proposal.status,
            actor_type="SYSTEM",
            actor_id=actor_id,
            proposal_hash=proposal.compute_hash(),
            provenance_refs=[p.ref_id for p in proposal.provenance_refs],
            reason=reason,
        )

    def reset_for_test(self) -> None:
        with self._lock:
            self._executed_proposals.clear()


__all__ = [
    "ExecutionBlockedError",
    "ExecutionGuard",
    "ExecutionVerification",
]
