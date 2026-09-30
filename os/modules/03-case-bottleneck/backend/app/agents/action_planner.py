"""
Action Planner (Sections 20-22).

Optimizes for safe workflow progress, evidence completeness, dependency
resolution, state correctness, and human control — NOT for "winning" the case.
Every action this agent proposes requires human approval (Section 23) before
anything is executed.
"""
from __future__ import annotations

import uuid

from sqlmodel import Session, select

from ..models import Bottleneck, BottleneckType, ActionItem, ActionStatus, ConfidenceLabel

TEMPLATES: dict[BottleneckType, dict] = {
    BottleneckType.DOCUMENT_BLOCKER: dict(
        action_type="prepare_information_request",
        purpose="Prepare a request for the missing document from the party who holds it.",
        required_actor="Legal-aid worker / Advocate",
        risk="LOW",
        verification_method="Check that a matching artifact is uploaded and tagged to this case and dependency.",
    ),
    BottleneckType.FILING_BLOCKER: dict(
        action_type="prepare_followup_draft",
        purpose="Prepare a follow-up communication requesting the pending filing.",
        required_actor="Advocate",
        risk="LOW",
        verification_method="Check registry/case record for the filing after follow-up.",
    ),
    BottleneckType.SERVICE_BLOCKER: dict(
        action_type="prepare_information_request",
        purpose="Request confirmation of service, or prepare a re-service request.",
        required_actor="Advocate / Process-serving staff",
        risk="LOW",
        verification_method="Check for a service affidavit or acknowledgment on file.",
    ),
    BottleneckType.EVIDENCE_BLOCKER: dict(
        action_type="prepare_review_packet",
        purpose="Compile existing evidence and flag the specific gap for the relevant witness/expert.",
        required_actor="Advocate",
        risk="LOW",
        verification_method="Check that the compiled packet references the missing item explicitly.",
    ),
    BottleneckType.CONTRADICTION_BLOCKER: dict(
        action_type="prepare_review_packet",
        purpose="Compile both conflicting sources side by side for human adjudication. This does NOT resolve the factual dispute.",
        required_actor="Advocate / Registrar",
        risk="MEDIUM",
        verification_method="Human confirms the packet fairly represents both sources.",
    ),
    BottleneckType.UNKNOWN_BLOCKER: dict(
        action_type="prepare_information_request",
        purpose="Escalate to the registry for manual investigation — there is not enough evidence for an automated recommendation.",
        required_actor="Registrar / Case Manager",
        risk="UNKNOWN",
        verification_method="Requires manual confirmation from the registry; outcome cannot be predicted.",
    ),
}

DEFAULT_TEMPLATE = dict(
    action_type="update_internal_case_task",
    purpose="Flag this item on the internal case task list for manual attention.",
    required_actor="Case Manager",
    risk="LOW",
    verification_method="Confirm the task was reviewed.",
)


class ActionPlannerAgent:
    name = "action-planner-agent"

    def run(self, session: Session, bottleneck: Bottleneck) -> ActionItem | None:
        existing = session.exec(
            select(ActionItem).where(
                ActionItem.bottleneck_id == bottleneck.id,
                ActionItem.status.in_([ActionStatus.PENDING_APPROVAL, ActionStatus.APPROVED, ActionStatus.EXECUTING]),
            )
        ).first()
        if existing:
            return existing

        template = TEMPLATES.get(bottleneck.type, DEFAULT_TEMPLATE)
        affected_desc = ", ".join(bottleneck.blocked_items) or "no currently-tracked transition"
        expected_effect = (
            f"If completed and verified, '{bottleneck.root_cause_candidate}' becomes satisfied, "
            f"potentially unblocking: {affected_desc}."
        )
        action = ActionItem(
            id=f"act_{uuid.uuid4().hex[:10]}",
            case_id=bottleneck.case_id,
            bottleneck_id=bottleneck.id,
            action_type=template["action_type"],
            purpose=template["purpose"],
            required_actor=template["required_actor"],
            status=ActionStatus.PENDING_APPROVAL,
            expected_effect=expected_effect,
            risk=template["risk"],
            verification_method=template["verification_method"],
        )
        session.add(action)
        session.commit()
        session.refresh(action)
        return action
