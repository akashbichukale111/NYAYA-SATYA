"""
State Reconciliation Agent (section 11 / 25 #4).

This is the ONLY place in the system that mutates the Case Digital Twin's
domain tables (Deadline, Order, Obligation, Hearing). It only runs after:
  1. the proposal has passed the Human Review Gate (approved/edited), and
  2. the Verification Agent has passed it.

It then:
  - applies the change to the relevant domain table
  - marks any prior conflicting/open row of the same kind SUPERSEDED (never deleted)
  - records a HUMAN_ACTION or AGENT_ACTION commit event
  - builds a new snapshot, diffs it against the previous StateVersion,
    records StateChange rows, and creates the new StateVersion
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    Case, ChangeProposal, Deadline, Order, Obligation, Hearing, Event, EventType,
    StateVersion, StateChange, ItemStatus,
)
from app.state_twin import build_snapshot
from app.diff import diff_snapshots
from app.freshness import compute_freshness
from app.agents.staleness_agent import supersede_open_deadlines
from app.agents.base import run_agent


def _apply_entity_change(db: Session, proposal: ChangeProposal, commit_event_id: str) -> str:
    """Create/update the concrete domain row for this proposal. Returns entity_id."""
    after = proposal.proposed_after
    case_id = proposal.case_id

    if proposal.entity_type == "deadline":
        existing_id = proposal.proposed_before.get("id")
        if existing_id:
            supersede_open_deadlines(db, case_id=case_id, except_id=None,
                                      superseding_event_id=commit_event_id, correlation_id="")
        row = Deadline(
            case_id=case_id, label=after.get("label", "Deadline"), due_date=after.get("due_date", ""),
            status=ItemStatus.OPEN.value, reason=proposal.reason, source_event_id=commit_event_id,
        )
        db.add(row)
        db.flush()
        return row.id

    if proposal.entity_type == "order":
        row = Order(
            case_id=case_id, order_date=after.get("order_date", ""), summary=after.get("summary", ""),
            status=ItemStatus.OPEN.value, source_event_id=commit_event_id,
        )
        db.add(row)
        db.flush()
        return row.id

    if proposal.entity_type == "obligation":
        row = Obligation(
            case_id=case_id, description=after.get("description", ""),
            owner_party=after.get("owner_party", "unassigned"), status=ItemStatus.OPEN.value,
            due_date=after.get("due_date", ""), source_event_id=commit_event_id,
        )
        db.add(row)
        db.flush()
        return row.id

    if proposal.entity_type == "hearing":
        row = Hearing(
            case_id=case_id, scheduled_date=after.get("scheduled_date", ""), occurred=False,
            status=ItemStatus.OPEN.value, source_event_id=commit_event_id,
        )
        db.add(row)
        db.flush()
        return row.id

    return ""


def commit_proposal(
    db: Session, *, proposal: ChangeProposal, reviewer: str, correlation_id: str, edited_after: dict | None = None,
) -> StateVersion:
    with run_agent(db, case_id=proposal.case_id, agent_name="StateReconciliationAgent",
                    correlation_id=correlation_id, input_summary=f"proposal_id={proposal.id}") as result:
        case = db.get(Case, proposal.case_id)
        if edited_after:
            proposal.proposed_after = {**proposal.proposed_after, **edited_after}

        before_snapshot = build_snapshot(db, proposal.case_id)

        commit_event = Event(
            case_id=proposal.case_id,
            event_type=EventType.HUMAN_ACTION.value,
            source=proposal.id,
            actor=reviewer,
            description=f"Reviewer '{reviewer}' committed proposal ({proposal.nature}) for {proposal.entity_type}.",
            structured_payload={"proposal_id": proposal.id, "nature": proposal.nature},
            confidence=proposal.confidence,
            provenance={"change_proposal_id": proposal.id, "source_event_id": proposal.source_event_id},
            correlation_id=correlation_id,
        )
        db.add(commit_event)
        db.flush()

        entity_id = _apply_entity_change(db, proposal, commit_event.event_id)

        proposal.review_status = "approved" if not edited_after else "edited"
        proposal.reviewer = reviewer
        proposal.reviewed_at = datetime.now(timezone.utc)

        db.flush()
        after_snapshot = build_snapshot(db, proposal.case_id)
        raw_diff = diff_snapshots(before_snapshot, after_snapshot)

        case.current_version_number += 1
        freshness = compute_freshness(db, proposal.case_id)
        version = StateVersion(
            case_id=proposal.case_id,
            version_number=case.current_version_number,
            label=f"{proposal.nature.upper()}: {proposal.entity_type}",
            triggering_event_id=commit_event.event_id,
            snapshot=after_snapshot,
            freshness=freshness["level"],
        )
        db.add(version)
        db.flush()

        proposal.resulting_version_number = version.version_number

        for collection, changes in raw_diff["entities"].items():
            for item in changes["added"]:
                db.add(StateChange(
                    case_id=proposal.case_id, from_version=version.version_number - 1,
                    to_version=version.version_number, category="ADDED", entity_type=collection,
                    entity_id=item["id"], after=item["after"], reason=proposal.reason,
                    source_event_id=commit_event.event_id,
                ))
            for item in changes["changed"]:
                category = "RESOLVED" if item["after"].get("status") == "resolved" else "CHANGED"
                db.add(StateChange(
                    case_id=proposal.case_id, from_version=version.version_number - 1,
                    to_version=version.version_number, category=category, entity_type=collection,
                    entity_id=item["id"], before=item["before"], after=item["after"],
                    reason=proposal.reason, source_event_id=commit_event.event_id,
                ))
            for item in changes["removed"]:
                db.add(StateChange(
                    case_id=proposal.case_id, from_version=version.version_number - 1,
                    to_version=version.version_number, category="REMOVED", entity_type=collection,
                    entity_id=item["id"], before=item["before"], reason=proposal.reason,
                    source_event_id=commit_event.event_id,
                ))

        db.commit()
        db.refresh(version)
        result["output_summary"] = f"version={version.version_number} entity_id={entity_id}"
        return version
