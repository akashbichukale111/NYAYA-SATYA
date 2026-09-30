"""
Continuity Health panel (section 18).

Deliberately NOT a single arbitrary "health score". Reports explainable
categories, each with the actual evidence (counts + example ids) behind it,
computed directly from the database rather than fabricated.
"""
from sqlalchemy.orm import Session

from app.models import (
    Conflict, Document, ChangeProposal, Event, Deadline, Obligation, Action,
    ItemStatus,
)


def compute_continuity_health(db: Session, case_id: str) -> dict:
    unresolved_conflicts = db.query(Conflict).filter(
        Conflict.case_id == case_id, Conflict.human_review_status == "pending").all()

    all_docs = db.query(Document).filter(Document.case_id == case_id).all()
    doc_ids_with_events = {
        e.source for e in db.query(Event).filter(Event.case_id == case_id).all() if e.source
    }
    unprocessed_artifacts = [d for d in all_docs if d.id not in doc_ids_with_events]

    pending_reviews = db.query(ChangeProposal).filter(
        ChangeProposal.case_id == case_id, ChangeProposal.review_status == "pending").all()

    # "Broken dependency": an obligation/action/deadline whose source_event_id
    # does not correspond to any Event row still in the case's history.
    all_event_ids = {e.event_id for e in db.query(Event).filter(Event.case_id == case_id).all()}

    def broken(rows):
        return [r.id for r in rows if r.source_event_id and r.source_event_id not in all_event_ids]

    broken_deadlines = broken(db.query(Deadline).filter(Deadline.case_id == case_id).all())
    broken_obligations = broken(db.query(Obligation).filter(Obligation.case_id == case_id).all())
    broken_actions = broken(db.query(Action).filter(Action.case_id == case_id).all())

    incomplete_actor_assignments = [
        a.id for a in db.query(Action).filter(Action.case_id == case_id).all()
        if a.assignee in ("", "unassigned") and a.status == ItemStatus.OPEN.value
    ]

    return {
        "unresolved_state_conflicts": {
            "count": len(unresolved_conflicts),
            "ids": [c.id for c in unresolved_conflicts],
        },
        "missing_source_references": {
            "count": len(broken_deadlines) + len(broken_obligations) + len(broken_actions),
            "deadline_ids": broken_deadlines, "obligation_ids": broken_obligations, "action_ids": broken_actions,
        },
        "unprocessed_artifacts": {
            "count": len(unprocessed_artifacts),
            "document_ids": [d.id for d in unprocessed_artifacts],
        },
        "unresolved_human_reviews": {
            "count": len(pending_reviews),
            "ids": [p.id for p in pending_reviews],
        },
        "incomplete_actor_assignments": {
            "count": len(incomplete_actor_assignments),
            "action_ids": incomplete_actor_assignments,
        },
    }
