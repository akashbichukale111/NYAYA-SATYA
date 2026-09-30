import uuid
from sqlmodel import Session

from .models import AuditEvent, utcnow


def new_correlation_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def record(
    session: Session,
    *,
    case_id: str,
    correlation_id: str,
    actor: str,
    event: str,
    source: str,
    result: dict | None = None,
) -> AuditEvent:
    entry = AuditEvent(
        id=f"audit_{uuid.uuid4().hex[:12]}",
        case_id=case_id,
        correlation_id=correlation_id,
        actor=actor,
        event=event,
        source=source,
        result=result or {},
        timestamp=utcnow(),
    )
    session.add(entry)
    session.commit()
    return entry
