"""
Builds the materialized "Case Digital Twin" snapshot used for:
  - StateVersion.snapshot (a cache, not the source of truth)
  - the State Diff Engine (app/diff.py)
  - the Current State / Command Center views

The relational tables (Deadline, Obligation, Order, Hearing, Evidence,
Action, Document) remain the source of truth; this module just projects
them into one dict shape per case at a point in time.
"""
from sqlalchemy.orm import Session

from app.models import (
    Case, Deadline, Obligation, Order, Hearing, Evidence, Action, Document,
    Conflict, ChangeProposal, ItemStatus,
)


def build_snapshot(db: Session, case_id: str) -> dict:
    case = db.get(Case, case_id)
    if not case:
        raise ValueError("case not found")

    def rows(model):
        return db.query(model).filter(model.case_id == case_id).all()

    deadlines = rows(Deadline)
    obligations = rows(Obligation)
    orders = rows(Order)
    hearings = rows(Hearing)
    evidence = rows(Evidence)
    actions = rows(Action)
    documents = rows(Document)
    conflicts = [c for c in rows(Conflict) if c.human_review_status == "pending"]
    pending_reviews = (
        db.query(ChangeProposal)
        .filter(ChangeProposal.case_id == case_id, ChangeProposal.review_status == "pending")
        .all()
    )

    snapshot = {
        "case_id": case.id,
        "title": case.title,
        "procedural_stage": case.procedural_stage,
        "deadlines": {
            d.id: {"label": d.label, "due_date": d.due_date, "status": d.status, "reason": d.reason}
            for d in deadlines if d.status != ItemStatus.SUPERSEDED.value
        },
        "obligations": {
            o.id: {"description": o.description, "owner_party": o.owner_party, "status": o.status,
                   "due_date": o.due_date}
            for o in obligations
        },
        "orders": {
            o.id: {"order_date": o.order_date, "summary": o.summary, "status": o.status}
            for o in orders
        },
        "hearings": {
            h.id: {"scheduled_date": h.scheduled_date, "occurred": h.occurred, "status": h.status,
                   "outcome_summary": h.outcome_summary}
            for h in hearings
        },
        "evidence": {
            e.id: {"label": e.label, "status": e.status} for e in evidence
        },
        "actions": {
            a.id: {"description": a.description, "assignee": a.assignee, "status": a.status}
            for a in actions
        },
        "documents": {
            d.id: {"filename": d.filename, "doc_type": d.doc_type} for d in documents
        },
        "open_items_count": (
            sum(1 for o in obligations if o.status == ItemStatus.OPEN.value)
            + sum(1 for a in actions if a.status == ItemStatus.OPEN.value)
        ),
        "unresolved_conflicts_count": len(conflicts),
        "pending_reviews_count": len(pending_reviews),
    }
    return snapshot
