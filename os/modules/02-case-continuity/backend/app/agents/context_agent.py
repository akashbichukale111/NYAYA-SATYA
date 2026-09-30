"""
Context / Handoff Agent (section 19 / 20 / 25 #7).

Builds the "what does the next human/agent need to know?" structured
handoff context: current state, recent changes, unresolved items, critical
evidence, pending actions, deadlines, contradictions, uncertainties,
previous decisions, and suggested review points.
"""
from sqlalchemy.orm import Session

from app.models import (
    Case, StateVersion, StateChange, Conflict, ChangeProposal, Obligation, Action, Deadline,
    Evidence, ItemStatus,
)
from app.state_twin import build_snapshot
from app.freshness import compute_freshness
from app.agents.base import run_agent


def build_handoff_context(db: Session, *, case_id: str, correlation_id: str) -> dict:
    with run_agent(db, case_id=case_id, agent_name="ContextHandoffAgent", correlation_id=correlation_id,
                    input_summary=f"case_id={case_id}") as result:
        case = db.get(Case, case_id)
        snapshot = build_snapshot(db, case_id)
        freshness = compute_freshness(db, case_id)

        latest_version = (
            db.query(StateVersion).filter(StateVersion.case_id == case_id)
            .order_by(StateVersion.version_number.desc()).first()
        )
        recent_changes = []
        if latest_version and latest_version.version_number > 0:
            recent_changes = (
                db.query(StateChange)
                .filter(StateChange.case_id == case_id, StateChange.to_version == latest_version.version_number)
                .all()
            )

        open_obligations = db.query(Obligation).filter(
            Obligation.case_id == case_id, Obligation.status == ItemStatus.OPEN.value).all()
        open_actions = db.query(Action).filter(
            Action.case_id == case_id, Action.status == ItemStatus.OPEN.value).all()
        open_deadlines = db.query(Deadline).filter(
            Deadline.case_id == case_id, Deadline.status == ItemStatus.OPEN.value).all()
        conflicts = db.query(Conflict).filter(
            Conflict.case_id == case_id, Conflict.human_review_status == "pending").all()
        pending_reviews = db.query(ChangeProposal).filter(
            ChangeProposal.case_id == case_id, ChangeProposal.review_status == "pending").all()
        critical_evidence = db.query(Evidence).filter(
            Evidence.case_id == case_id, Evidence.status != ItemStatus.SUPERSEDED.value).all()

        context = {
            "case_id": case_id,
            "case_title": case.title,
            "current_state": snapshot,
            "state_freshness": freshness,
            "recent_changes": [
                {"category": c.category, "entity_type": c.entity_type, "reason": c.reason,
                 "source_event_id": c.source_event_id}
                for c in recent_changes
            ],
            "unresolved_items": {
                "open_obligations": [{"id": o.id, "description": o.description} for o in open_obligations],
                "open_actions": [{"id": a.id, "description": a.description, "assignee": a.assignee} for a in open_actions],
                "open_deadlines": [{"id": d.id, "label": d.label, "due_date": d.due_date} for d in open_deadlines],
            },
            "critical_evidence": [{"id": e.id, "label": e.label, "status": e.status} for e in critical_evidence],
            "pending_actions": [{"id": a.id, "description": a.description} for a in open_actions],
            "deadlines": [{"id": d.id, "label": d.label, "due_date": d.due_date} for d in open_deadlines],
            "contradictions": [
                {"id": c.id, "type": c.conflict_type, "what_conflicts": c.what_conflicts,
                 "possible_explanation": c.possible_explanation}
                for c in conflicts
            ],
            "uncertainties": [
                {"id": p.id, "entity_type": p.entity_type, "nature": p.nature, "reason": p.reason,
                 "confidence": p.confidence}
                for p in pending_reviews
            ],
            "suggested_review_points": (
                [f"Resolve conflict: {c.what_conflicts}" for c in conflicts]
                + [f"Review pending proposal on {p.entity_type} ({p.nature})" for p in pending_reviews]
            ),
        }
        result["output_summary"] = f"open_obligations={len(open_obligations)} conflicts={len(conflicts)}"
        return context
