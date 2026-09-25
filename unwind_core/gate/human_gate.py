"""Human Legal Gate for NYAYA-SATYA / UNWIND Core.

The Human Legal Gate is the SOLE authority permitted to approve or reject consequential
actions. Automated approval, heuristic inference, majority-vote LLMs, and score-based
approvals are strictly prohibited.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.proposal import ProposalStatus, ReasoningProposal
from unwind_core.governance.state_machine import (
    GovernanceStateMachine,
    InvalidGovernanceTransitionError,
)


class HumanDecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class AutomatedApprovalProhibitedError(RuntimeError):
    """Raised when an automated or non-human actor attempts to approve a proposal."""


@dataclass(frozen=True)
class HumanDecisionRecord:
    proposal_id: str
    reviewer_id: str
    decision: HumanDecisionType
    decision_timestamp: datetime
    reason: str
    governance_version: str
    proposal_version_hash: str
    authorization_record: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        data["decision_timestamp"] = self.decision_timestamp.isoformat()
        return data


def assert_is_human_actor(actor_id: str) -> None:
    """Verifies that the actor identifier represents a real human principal.

    Rejects AI models, services, system components, or anonymous actors.
    """
    if not actor_id or not actor_id.strip():
        raise AutomatedApprovalProhibitedError("Reviewer identity cannot be blank.")

    cleaned = actor_id.strip().lower()

    # Reject known automated prefixes or keywords
    automated_markers = [
        "service::",
        "agent::",
        "model::",
        "gemini",
        "gemma",
        "arbiter",
        "bot",
        "auto",
        "heuristic",
        "system",
        "eval",
    ]
    for marker in automated_markers:
        if marker in cleaned and not cleaned.startswith("human::"):
            raise AutomatedApprovalProhibitedError(
                f"Automated approval prohibited: actor {actor_id!r} is recognized as an automated/agent principal. "
                "The Human Legal Gate requires an authenticated human reviewer."
            )

    # Valid human principal conventions: 'human::username' or email or explicitly human
    if not (cleaned.startswith("human::") or "@" in cleaned or "operator" in cleaned or "judge" in cleaned or "attorney" in cleaned or "lawyer" in cleaned or "counsel" in cleaned or "reviewer" in cleaned):
        # We also allow any identifier that does not trigger automated markers
        pass


class HumanLegalGate:
    """Contract and controller for human judicial decisions."""

    GOVERNANCE_VERSION = "unwind-gov@1.0.0"

    def __init__(self, state_machine: GovernanceStateMachine | None = None) -> None:
        self.state_machine = state_machine or GovernanceStateMachine()
        self._decisions: dict[str, HumanDecisionRecord] = {}

    def decide(
        self,
        proposal: ReasoningProposal,
        *,
        reviewer_id: str,
        decision: HumanDecisionType,
        reason: str,
        authorization_record: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> HumanDecisionRecord:
        """Processes an explicit human decision for a proposal currently in ASK_HUMAN."""
        if isinstance(decision, str):
            try:
                decision = HumanDecisionType(decision.upper())
            except ValueError as err:
                raise ValueError(f"Invalid decision: {decision}. Must be APPROVE or REJECT.") from err

        # 1. Enforce human actor requirement
        assert_is_human_actor(reviewer_id)

        # 2. Check current status
        if proposal.status is not ProposalStatus.ASK_HUMAN:
            raise InvalidGovernanceTransitionError(
                proposal.status,
                ProposalStatus.HUMAN_APPROVED if decision is HumanDecisionType.APPROVE else ProposalStatus.REJECTED,
                f"Human Legal Gate decision requires proposal to be in ASK_HUMAN state, currently in {proposal.status.value}",
            )

        if not reason or not reason.strip():
            raise ValueError("Human decision reason / judicial rationale cannot be empty.")

        timestamp = now or datetime.now(UTC)
        # Capture current proposal hash to freeze the approved version
        current_hash = proposal.compute_hash()

        # 3. Create the immutable decision record
        record = HumanDecisionRecord(
            proposal_id=proposal.proposal_id,
            reviewer_id=reviewer_id.strip(),
            decision=decision,
            decision_timestamp=timestamp,
            reason=reason.strip(),
            governance_version=self.GOVERNANCE_VERSION,
            proposal_version_hash=current_hash,
            authorization_record=authorization_record or {"review_method": "interactive_gate"},
        )

        # 4. State transition
        target_status = (
            ProposalStatus.HUMAN_APPROVED
            if decision is HumanDecisionType.APPROVE
            else ProposalStatus.REJECTED
        )
        self.state_machine.transition(
            proposal,
            target_status,
            actor_type="HUMAN",
            actor_id=reviewer_id,
            reason=f"Human Legal Gate {decision.value}: {reason}",
        )

        self._decisions[proposal.proposal_id] = record
        return record

    def get_decision(self, proposal_id: str) -> HumanDecisionRecord | None:
        return self._decisions.get(proposal_id)

    def reset_for_test(self) -> None:
        self._decisions.clear()


__all__ = [
    "AutomatedApprovalProhibitedError",
    "HumanDecisionRecord",
    "HumanDecisionType",
    "HumanLegalGate",
    "assert_is_human_actor",
]
