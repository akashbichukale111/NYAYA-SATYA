"""
Action execution (Section 24) + Verification Agent (Section 25).

DEMO-MODE NOTE: "execution" here never files anything with a real court or
touches any external system — per Section 24 ("No autonomous court filing").
It simulates the *result* of a human having carried out the approved action
(e.g. "document was uploaded"), using deterministic outcomes wired into the
demo scenarios (see demo_data.py). This lets the verification step be real
and meaningful — "did the result actually satisfy what was required?" — even
though the underlying event is simulated. This is clearly labelled
`"demo": True` in every action result returned by the API.
"""
from __future__ import annotations

import uuid

from sqlmodel import Session

from ..models import ActionItem, ActionStatus, VerificationRecord, utcnow


def execute_action(session: Session, action: ActionItem, case_demo_scenario: str | None) -> ActionItem:
    """Simulate carrying out an approved action. Never assumes success (Section 25)."""
    action.status = ActionStatus.EXECUTING
    session.add(action)
    session.commit()

    # Deterministic demo outcomes per scenario (see demo_data.py comments).
    if case_demo_scenario == "G":
        # Case G is deliberately designed so the uploaded artifact references
        # the wrong case — verification is EXPECTED to fail.
        result = {
            "demo": True,
            "artifact": "uploaded_annexure_wrong_case.txt",
            "case_reference": "CASE-999",  # deliberately mismatched
        }
    elif case_demo_scenario == "I":
        # Genuinely unknown — execution produces no conclusive artifact.
        result = {"demo": True, "artifact": None, "note": "Registry inquiry initiated; no artifact yet."}
    else:
        result = {"demo": True, "artifact": "requested_document.txt", "case_reference": action.case_id}

    action.result = result
    action.executed_at = utcnow()
    action.status = ActionStatus.VERIFYING
    session.add(action)
    session.commit()
    session.refresh(action)
    return action


class VerificationAgent:
    name = "verification-agent"

    def verify(self, session: Session, action: ActionItem) -> VerificationRecord:
        result = action.result or {}
        if result.get("artifact") is None:
            passed = False
            details = "No artifact was produced — manual confirmation required. Bottleneck remains open."
        elif result.get("case_reference") and result["case_reference"] != action.case_id:
            passed = False
            details = (
                f"Artifact's case reference ({result['case_reference']}) does not match "
                f"this case ({action.case_id}). Verification failed."
            )
        else:
            passed = True
            details = "Artifact present and correctly associated with this case."

        record = VerificationRecord(
            id=f"ver_{uuid.uuid4().hex[:10]}",
            action_id=action.id,
            case_id=action.case_id,
            passed=passed,
            details=details,
        )
        session.add(record)

        action.status = ActionStatus.COMPLETED if passed else ActionStatus.VERIFICATION_FAILED
        session.add(action)
        session.commit()
        session.refresh(record)
        return record
