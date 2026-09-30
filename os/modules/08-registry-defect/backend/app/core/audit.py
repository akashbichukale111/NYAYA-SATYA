"""Append-only audit logging.

AuditEvent rows are never updated or deleted by any code path in this
application (no UPDATE/DELETE statements target audit_events anywhere
in the codebase). record() is the single write path so every audited
action has a consistent shape.
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow


def record(
    db: Session,
    *,
    case_id: str | None,
    actor_user_id: str | None,
    actor_role: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    reason: str | None = None,
    provenance: str | None = None,
) -> models.AuditEvent:
    event = models.AuditEvent(
        id=new_id("aud"),
        case_id=case_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        timestamp=utcnow().isoformat(),
        provenance=provenance,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
