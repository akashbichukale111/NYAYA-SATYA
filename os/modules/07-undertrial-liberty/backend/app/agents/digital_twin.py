"""
Liberty Digital Twin.

Builds the continuously-updated, case-scoped summary of everything the
system currently believes about a case's liberty-relevant procedural
state. This is an OPERATIONAL SUMMARY, never a legal conclusion. It is
also the shape returned by the NYAYA-SATYA integration adapter.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import orm
from app.core.enums import CurrentCustodyStatus, CurrentStatusConfidence


def _serialize_custody_event(e: orm.CustodyEvent):
    return {
        "id": e.id, "event_type": e.event_type, "event_date": e.event_date,
        "date_type": e.date_type, "verification_status": e.verification_status,
        "source_document_id": e.source_document_id,
    }


def compute_current_custody_status(custody_events, conflicts) -> tuple[str, str]:
    """
    Returns (CurrentCustodyStatus, confidence_note). This NEVER determines
    lawful/unlawful detention -- only whether our own records are known,
    unverified, conflicting, or absent.
    """
    if not custody_events:
        return CurrentCustodyStatus.CUSTODY_STATE_UNKNOWN.value, \
            "No custody events are recorded for this case."
    open_custody_conflicts = [c for c in conflicts if c.entity_type == "CustodyEvent" and c.status == "OPEN"]
    if open_custody_conflicts:
        return CurrentCustodyStatus.CUSTODY_STATE_CONFLICTING.value, \
            "Two or more sources disagree about custody information."
    verified = [e for e in custody_events if e.verification_status == "SOURCE_FACT"]
    if verified:
        return CurrentCustodyStatus.CUSTODY_STATE_KNOWN_VERIFIED.value, \
            "The most recent custody event is supported by a source document."
    return CurrentCustodyStatus.CUSTODY_STATE_KNOWN_UNVERIFIED.value, \
        "Custody events are recorded but not yet verified against a source."


def build_digital_twin(db: Session, case_id: str) -> dict:
    case = db.query(orm.Case).filter(orm.Case.id == case_id).first()
    if not case:
        return {}

    custody_events = db.query(orm.CustodyEvent).filter(orm.CustodyEvent.case_id == case_id) \
        .order_by(orm.CustodyEvent.event_date.desc().nullslast()).all()
    hearings = db.query(orm.Hearing).filter(orm.Hearing.case_id == case_id).all()
    orders = db.query(orm.Order).filter(orm.Order.case_id == case_id).all()
    bail_events = db.query(orm.BailEvent).filter(orm.BailEvent.case_id == case_id).all()
    release_events = db.query(orm.ReleaseRelatedEvent).filter(orm.ReleaseRelatedEvent.case_id == case_id).all()
    conflicts = db.query(orm.Conflict).filter(orm.Conflict.case_id == case_id).all()
    open_conflicts = [c for c in conflicts if c.status == "OPEN"]
    attention_items = db.query(orm.AttentionItem).filter(
        orm.AttentionItem.case_id == case_id, orm.AttentionItem.status == "OPEN"
    ).all()
    pending_reviews = db.query(orm.ReviewTask).filter(
        orm.ReviewTask.case_id == case_id, orm.ReviewTask.status == "PENDING"
    ).all()
    documents = db.query(orm.Document).filter(orm.Document.case_id == case_id).all()

    custody_status, custody_note = compute_current_custody_status(custody_events, conflicts)
    latest_verified_event = next((e for e in custody_events if e.verification_status == "SOURCE_FACT"), None)

    today = datetime.now(timezone.utc).date()
    upcoming = []
    for h in hearings:
        if h.hearing_date:
            try:
                d = datetime.fromisoformat(h.hearing_date).date()
                if d >= today:
                    upcoming.append({"type": "hearing", "id": h.id, "date": h.hearing_date, "purpose": h.purpose})
            except ValueError:
                pass

    missing_information = []
    if not custody_events:
        missing_information.append("No custody events recorded.")
    if not hearings:
        missing_information.append("No hearings recorded.")
    if not orders:
        missing_information.append("No orders recorded.")
    for h in hearings:
        if h.status == "HELD_RESULT_RECORDED" and not any(o.related_hearing_id == h.id for o in orders):
            missing_information.append(f"Hearing {h.id} has a result but no linked order.")

    return {
        "case_id": case.id,
        "case_reference": case.case_reference,
        "is_demo": case.is_demo,
        "custody_state": custody_status,
        "custody_state_confidence": custody_note,
        "latest_verified_event": _serialize_custody_event(latest_verified_event) if latest_verified_event else None,
        "current_custody_events": [_serialize_custody_event(e) for e in custody_events],
        "upcoming_tracked_events": upcoming,
        "recent_orders": [{"id": o.id, "status": o.status, "summary": o.summary,
                            "mentioned_date": o.mentioned_date} for o in orders],
        "bail_events": [{"id": b.id, "event_type": b.event_type, "event_date": b.event_date,
                          "verification_status": b.verification_status} for b in bail_events],
        "release_events": [{"id": r.id, "event_type": r.event_type,
                             "current_status_confidence": r.current_status_confidence} for r in release_events],
        "pending_reviews": [{"id": t.id, "task_type": t.task_type, "description": t.description}
                             for t in pending_reviews],
        "missing_information": missing_information,
        "conflicts": [{"id": c.id, "field": c.field_name, "value_a": c.value_a, "value_b": c.value_b,
                        "status": c.status} for c in open_conflicts],
        "dependency_items_blocked_count": None,  # populated by API layer from dependency graph
        "attention_items": [{"id": a.id, "category": a.category, "severity": a.severity, "reason": a.reason,
                              "requires_human_review": a.requires_human_review} for a in attention_items],
        "documents_ingested": len(documents),
        "provenance_refs": [d.id for d in documents],
        "last_updated": case.updated_at.isoformat() if case.updated_at else None,
    }
