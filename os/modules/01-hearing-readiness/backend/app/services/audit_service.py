"""
Append-only audit semantics (section 20). Deliberately exposes no
update/delete function -- only log_event() and read helpers -- so the
"append-only" property is a property of the code surface, not just a
convention documented elsewhere.
"""
from __future__ import annotations

from app.models.audit import AuditEvent


def log_event(db, *, case_id: str | None, actor: str, event_type: str, action: str,
              input_ref, result, correlation_id: str) -> AuditEvent:
    event = AuditEvent(
        case_id=case_id, actor=actor, event_type=event_type, action=action,
        input_ref=input_ref, result=result, correlation_id=correlation_id,
    )
    db.add(event)
    db.flush()
    return event


def get_case_audit(db, case_id: str) -> list[dict]:
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    return [e.to_dict() for e in events]
