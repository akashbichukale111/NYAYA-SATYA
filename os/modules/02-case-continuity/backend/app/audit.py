from sqlalchemy.orm import Session

from app.models import AuditEvent


def log_audit(
    db: Session,
    *,
    case_id: str = "",
    actor: str = "system",
    event_type: str,
    correlation_id: str = "",
    source: str = "",
    result: str = "",
    detail: dict | None = None,
    commit: bool = True,
) -> AuditEvent:
    entry = AuditEvent(
        case_id=case_id,
        actor=actor,
        event_type=event_type,
        correlation_id=correlation_id,
        source=source,
        result=result,
        detail=detail or {},
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
