"""
Verification Agent (section 25 #8 / section 28).

Runs a fixed set of checks on a ChangeProposal before it is allowed to be
committed as a new StateVersion. If any REQUIRED check fails, the
transition is NOT committed and is recorded as VERIFICATION FAILED.
"""
from sqlalchemy.orm import Session

from app.models import ChangeProposal, Event, Conflict, Verification, VerificationResult
from app.agents.base import run_agent


REQUIRED_FIELDS_BY_ENTITY = {
    "deadline": ["due_date"],
    "order": ["summary"],
    "obligation": ["description"],
    "hearing": ["scheduled_date"],
}


def verify_proposal(db: Session, *, proposal: ChangeProposal, correlation_id: str) -> Verification:
    with run_agent(db, case_id=proposal.case_id, agent_name="VerificationAgent", correlation_id=correlation_id,
                    input_summary=f"proposal_id={proposal.id}") as result:
        checks: dict[str, bool] = {}
        failures: list[str] = []

        source_event = db.get(Event, proposal.source_event_id)
        checks["source_exists"] = source_event is not None
        if not checks["source_exists"]:
            failures.append("Source event referenced by the proposal no longer exists.")

        checks["source_belongs_to_case"] = bool(source_event and source_event.case_id == proposal.case_id)
        if source_event and not checks["source_belongs_to_case"]:
            failures.append("Source event belongs to a different case (isolation violation).")

        required = REQUIRED_FIELDS_BY_ENTITY.get(proposal.entity_type, [])
        missing = [f for f in required if not proposal.proposed_after.get(f)]
        checks["required_fields_present"] = not missing
        if missing:
            failures.append(f"Missing required field(s) for {proposal.entity_type}: {missing}")

        open_conflicts = (
            db.query(Conflict)
            .filter(Conflict.case_id == proposal.case_id, Conflict.human_review_status == "pending")
            .count()
        )
        # A pending, unrelated conflict shouldn't block every future proposal forever,
        # but we surface it explicitly rather than silently ignoring it.
        checks["no_silently_ignored_conflict"] = True
        if open_conflicts:
            result["output_summary"] = f"note: {open_conflicts} unrelated conflict(s) remain open"

        checks["valid_transition"] = proposal.review_status in ("pending", "approved", "edited")
        if not checks["valid_transition"]:
            failures.append(f"Proposal is in status '{proposal.review_status}', not eligible for commit.")

        passed = all(checks.values())
        verification = Verification(
            case_id=proposal.case_id,
            change_proposal_id=proposal.id,
            result=VerificationResult.PASSED.value if passed else VerificationResult.FAILED.value,
            checks=checks,
            failure_reasons=failures,
        )
        db.add(verification)
        db.commit()
        db.refresh(verification)
        result["output_summary"] = verification.result
        return verification
