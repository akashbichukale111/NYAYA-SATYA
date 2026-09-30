from sqlalchemy.orm import Session
from app.models.models import AuditEvent


def record_event(db: Session, case_id: str, event_type: str, actor: str = "system",
                  workflow_id: str = None, task_id: str = None, payload: dict = None) -> AuditEvent:
    event = AuditEvent(
        case_id=case_id,
        workflow_id=workflow_id,
        task_id=task_id,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    return event
