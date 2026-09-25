"""Deterministic Governance State Machine for UNWIND Core.

Enforces non-negotiable state transition rules:
PROPOSED -> GOVERNANCE_REVIEW -> ASK_HUMAN -> [HUMAN_APPROVED | REJECTED]
HUMAN_APPROVED -> EXECUTED

All illegal or bypassed transitions (e.g., PROPOSED -> EXECUTED, ASK_HUMAN -> EXECUTED)
raise InvalidGovernanceTransitionError.
"""

from __future__ import annotations

import threading
from typing import Any

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from unwind_core.governance.audit import AuditEventType, AuditStore, get_audit_store


class InvalidGovernanceTransitionError(ValueError):
    """Raised when an illegal governance state transition is attempted."""

    def __init__(self, from_status: ProposalStatus, to_status: ProposalStatus, reason: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Illegal governance transition from {from_status.value} to {to_status.value}: {reason}"
        )


class GovernanceStateMachine:
    """Manages governed state transitions for reasoning proposals."""

    # Explicitly allowed transitions
    _VALID_TRANSITIONS: dict[ProposalStatus, frozenset[ProposalStatus]] = {
        ProposalStatus.PROPOSED: frozenset({ProposalStatus.GOVERNANCE_REVIEW, ProposalStatus.FAILED}),
        ProposalStatus.GOVERNANCE_REVIEW: frozenset({ProposalStatus.ASK_HUMAN, ProposalStatus.FAILED}),
        ProposalStatus.ASK_HUMAN: frozenset({
            ProposalStatus.HUMAN_APPROVED,
            ProposalStatus.REJECTED,
            ProposalStatus.FAILED,
        }),
        ProposalStatus.HUMAN_APPROVED: frozenset({ProposalStatus.EXECUTED, ProposalStatus.FAILED}),
        ProposalStatus.REJECTED: frozenset({ProposalStatus.FAILED}),
        ProposalStatus.EXECUTED: frozenset(),  # Terminal state
        ProposalStatus.FAILED: frozenset(),    # Terminal state
    }

    def __init__(self, audit_store: AuditStore | None = None) -> None:
        self.audit_store = audit_store or get_audit_store()
        self._lock = threading.Lock()

    def transition(
        self,
        proposal: ReasoningProposal,
        target_status: ProposalStatus,
        *,
        actor_type: str,
        actor_id: str,
        reason: str,
    ) -> ProposalStatus:
        """Transitions proposal to target_status with strict validation and audit logging."""
        with self._lock:
            current_status = proposal.status

            # Check if transition is explicitly allowed
            allowed = self._VALID_TRANSITIONS.get(current_status, frozenset())
            if target_status not in allowed:
                # Provide clear diagnosis of why it failed
                explanation = (
                    f"Direct jump from {current_status.value} to {target_status.value} violates governance. "
                )
                if current_status is ProposalStatus.PROPOSED and target_status is ProposalStatus.EXECUTED:
                    explanation += "AI reasoning proposals cannot execute directly without governance and human approval."
                elif current_status is ProposalStatus.PROPOSED and target_status is ProposalStatus.HUMAN_APPROVED:
                    explanation += "Proposals must undergo GOVERNANCE_REVIEW and ASK_HUMAN before approval."
                elif current_status is ProposalStatus.ASK_HUMAN and target_status is ProposalStatus.EXECUTED:
                    explanation += "Proposals in ASK_HUMAN require explicit human approval before execution."
                elif current_status is ProposalStatus.REJECTED and target_status is ProposalStatus.EXECUTED:
                    explanation += "Rejected proposals can never be executed."
                else:
                    explanation += f"Allowed transitions from {current_status.value} are: {[s.value for s in allowed]}."

                raise InvalidGovernanceTransitionError(current_status, target_status, explanation)

            # Enforce actor role requirements
            if target_status in {ProposalStatus.HUMAN_APPROVED, ProposalStatus.REJECTED}:
                if actor_type != "HUMAN":
                    raise InvalidGovernanceTransitionError(
                        current_status,
                        target_status,
                        f"Target status {target_status.value} requires actor_type='HUMAN', but got {actor_type!r}.",
                    )

            # Map audit event type
            event_type = self._map_audit_event(target_status)

            # Update status
            proposal.status = target_status

            # Record audit log
            self.audit_store.record_event(
                proposal_id=proposal.proposal_id,
                case_id=proposal.case_id,
                event_type=event_type,
                previous_status=current_status,
                new_status=target_status,
                actor_type=actor_type,
                actor_id=actor_id,
                proposal_hash=proposal.compute_hash(),
                provenance_refs=[p.ref_id for p in proposal.provenance_refs],
                reason=reason,
            )

            return target_status

    def _map_audit_event(self, status: ProposalStatus) -> AuditEventType:
        mapping = {
            ProposalStatus.GOVERNANCE_REVIEW: AuditEventType.GOVERNANCE_REVIEWED,
            ProposalStatus.ASK_HUMAN: AuditEventType.ASK_HUMAN,
            ProposalStatus.HUMAN_APPROVED: AuditEventType.HUMAN_APPROVED,
            ProposalStatus.REJECTED: AuditEventType.HUMAN_REJECTED,
            ProposalStatus.EXECUTED: AuditEventType.EXECUTED,
            ProposalStatus.FAILED: AuditEventType.EXECUTION_BLOCKED,
        }
        return mapping.get(status, AuditEventType.GOVERNANCE_REVIEWED)


__all__ = [
    "GovernanceStateMachine",
    "InvalidGovernanceTransitionError",
]
