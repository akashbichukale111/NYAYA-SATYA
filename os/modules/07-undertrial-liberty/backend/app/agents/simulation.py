"""
Counterfactual Simulation and Liberty Crash Test.

Both use a real database SAVEPOINT: the requested mutation is actually
applied to a nested transaction, the digital twin / attention engine /
dependency graph are recomputed against that mutated state, the result is
captured, and then the nested transaction is ALWAYS rolled back. This
means the simulation reflects genuine system behavior (not a canned
response) while guaranteeing production data is never mutated by a
simulation or crash test run.
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models import orm
from app.agents.digital_twin import build_digital_twin
from app.agents.attention import run_attention_engine
from app.agents.dependency import rebuild_dependency_graph
from app.agents.time_machine import diff_snapshots


SUPPORTED_SIMULATION_EVENTS = {
    "REMOVE_CUSTODY_DOCUMENT": "Remove a document and detach records sourced from it",
    "REMOVE_HEARING_RESULT": "Clear a hearing's recorded result",
    "MARK_CUSTODY_EVENT_UNVERIFIED": "Mark a custody event as UNVERIFIED",
    "INTRODUCE_CONFLICTING_CUSTODY_DATE": "Add a conflicting custody event with a different date",
    "REMOVE_ORDER": "Delete an order record",
    "SUPERSEDE_ORDER": "Mark an order as ORDER_SUPERSEDED",
    "REMOVE_BAIL_EVENT": "Delete a bail event record",
    "INVALIDATE_PROVENANCE": "Strip source_document_id from a record",
    "CREATE_MISSING_HEARING_RESULT": "Add a hearing with STATUS_UNKNOWN and no result",
    "CREATE_STALE_CASE_STATE": "Backdate the case's updated_at to simulate staleness",
}


def _apply_event(db: Session, case_id: str, event_type: str, target_entity_id: Optional[str]):
    """Applies one simulated mutation inside the caller's transaction."""
    if event_type == "REMOVE_CUSTODY_DOCUMENT" and target_entity_id:
        doc = db.query(orm.Document).filter(orm.Document.id == target_entity_id, orm.Document.case_id == case_id).first()
        if doc:
            for e in db.query(orm.CustodyEvent).filter(orm.CustodyEvent.source_document_id == doc.id):
                e.source_document_id = None
            db.delete(doc)

    elif event_type == "REMOVE_HEARING_RESULT" and target_entity_id:
        h = db.query(orm.Hearing).filter(orm.Hearing.id == target_entity_id, orm.Hearing.case_id == case_id).first()
        if h:
            h.status = "HELD_RESULT_MISSING"
            h.result_summary = None

    elif event_type == "MARK_CUSTODY_EVENT_UNVERIFIED" and target_entity_id:
        e = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.id == target_entity_id, orm.CustodyEvent.case_id == case_id).first()
        if e:
            e.verification_status = "UNVERIFIED"

    elif event_type == "INTRODUCE_CONFLICTING_CUSTODY_DATE" and target_entity_id:
        e = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.id == target_entity_id, orm.CustodyEvent.case_id == case_id).first()
        if e:
            fake_conflict_event = orm.CustodyEvent(
                case_id=case_id, event_type=e.event_type,
                event_date="1999-01-01" if e.event_date != "1999-01-01" else "2000-01-01",
                date_type="SOURCE_EXPLICIT_DATE", verification_status="UNVERIFIED",
                source_document_id="simulated_conflicting_source",
                source_text_snippet="[SIMULATED] conflicting date for crash test",
            )
            db.add(fake_conflict_event)
            db.flush()
            from app.agents.reconciliation import run_all_reconciliation
            run_all_reconciliation(db, case_id, commit=False)

    elif event_type == "REMOVE_ORDER" and target_entity_id:
        o = db.query(orm.Order).filter(orm.Order.id == target_entity_id, orm.Order.case_id == case_id).first()
        if o:
            db.delete(o)

    elif event_type == "SUPERSEDE_ORDER" and target_entity_id:
        o = db.query(orm.Order).filter(orm.Order.id == target_entity_id, orm.Order.case_id == case_id).first()
        if o:
            o.status = "ORDER_SUPERSEDED"

    elif event_type == "REMOVE_BAIL_EVENT" and target_entity_id:
        b = db.query(orm.BailEvent).filter(orm.BailEvent.id == target_entity_id, orm.BailEvent.case_id == case_id).first()
        if b:
            db.delete(b)

    elif event_type == "INVALIDATE_PROVENANCE" and target_entity_id:
        for model in (orm.CustodyEvent, orm.Hearing, orm.Order, orm.BailEvent, orm.ReleaseRelatedEvent):
            row = db.query(model).filter(model.id == target_entity_id, model.case_id == case_id).first()
            if row:
                row.source_document_id = None
                row.source_text_snippet = None

    elif event_type == "CREATE_MISSING_HEARING_RESULT":
        h = orm.Hearing(case_id=case_id, status="STATUS_UNKNOWN", date_type="UNKNOWN_DATE",
                         verification_status="UNVERIFIED", purpose="[SIMULATED] hearing with no result")
        db.add(h)

    elif event_type == "CREATE_STALE_CASE_STATE":
        from datetime import datetime, timedelta, timezone
        case = db.query(orm.Case).filter(orm.Case.id == case_id).first()
        if case:
            case.updated_at = datetime.now(timezone.utc) - timedelta(days=90)

    db.flush()


def run_simulation(db: Session, case_id: str, event_type: str, target_entity_id: Optional[str] = None) -> dict:
    if event_type not in SUPPORTED_SIMULATION_EVENTS:
        return {"error": f"Unsupported simulation event type: {event_type}",
                "supported": list(SUPPORTED_SIMULATION_EVENTS.keys())}

    before_twin = build_digital_twin(db, case_id)
    before_conflicts = len(db.query(orm.Conflict).filter(orm.Conflict.case_id == case_id).all())

    nested = db.begin_nested()
    try:
        _apply_event(db, case_id, event_type, target_entity_id)
        # commit=False on every call below: this is the fix that makes the
        # SAVEPOINT rollback below actually work. Any inner db.commit() call
        # here would release the SAVEPOINT into the parent transaction and
        # permanently persist the simulated mutation -- see
        # app/agents/attention.py and app/agents/dependency.py for the
        # matching commit/flush split, and docs/architecture.md for the
        # full incident writeup of this bug.
        run_attention_engine(db, case_id, commit=False)
        rebuild_dependency_graph(db, case_id, commit=False)
        after_twin = build_digital_twin(db, case_id)
        after_conflicts = db.query(orm.Conflict).filter(orm.Conflict.case_id == case_id).all()
        new_attention = db.query(orm.AttentionItem).filter(
            orm.AttentionItem.case_id == case_id, orm.AttentionItem.status == "OPEN"
        ).all()
        affected_attention = [{"category": a.category, "severity": a.severity, "reason": a.reason}
                               for a in new_attention]
    finally:
        nested.rollback()  # ALWAYS rollback: simulations never mutate production state

    diff = diff_snapshots(before_twin, after_twin)

    return {
        "event_type": event_type,
        "description": SUPPORTED_SIMULATION_EVENTS[event_type],
        "target_entity_id": target_entity_id,
        "before": before_twin,
        "after": after_twin,
        "diff": diff,
        "affected_attention_items": affected_attention,
        "new_conflicts_introduced": len(after_conflicts) - before_conflicts,
        "human_review_required": any(a["severity"] == "REQUIRES_HUMAN_REVIEW" for a in affected_attention),
        "production_state_mutated": False,
    }


def run_crash_test(db: Session, case_id: str, event_type: str, target_entity_id: Optional[str] = None) -> dict:
    """Crash Test uses the same rollback-guaranteed mechanism as simulation,
    framed for adversarial 'what breaks' testing rather than what-if planning."""
    result = run_simulation(db, case_id, event_type, target_entity_id)
    result["mode"] = "CRASH_TEST"
    return result
