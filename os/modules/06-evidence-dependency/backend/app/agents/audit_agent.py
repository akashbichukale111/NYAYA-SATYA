"""
Audit Agent.

Every other agent already writes to the append-only AuditEvent log via
review_service.log_audit_event -- this module is the queryable read
surface for that log (filter by actor/action/target), plus a plain
structured record() passthrough for agents/services that want a
one-line import instead of reaching into review_service directly.
"""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.orm import AuditEvent
from app.services.review_service import log_audit_event


def record(db: Session, case_id: str, actor: str, action: str, **kwargs) -> AuditEvent:
    return log_audit_event(db, case_id, actor=actor, action=action, **kwargs)


def query(
    db: Session, case_id: str, actor: Optional[str] = None,
    action: Optional[str] = None, target_type: Optional[str] = None,
) -> List[Dict]:
    q = db.query(AuditEvent).filter(AuditEvent.case_id == case_id)
    if actor:
        q = q.filter(AuditEvent.actor == actor)
    if action:
        q = q.filter(AuditEvent.action == action)
    if target_type:
        q = q.filter(AuditEvent.target_type == target_type)
    events = q.order_by(AuditEvent.created_at.desc()).all()
    return [
        {"id": e.id, "actor": e.actor, "actor_type": e.actor_type, "action": e.action,
         "target_type": e.target_type, "target_id": e.target_id, "detail": e.detail,
         "created_at": e.created_at.isoformat()}
        for e in events
    ]
