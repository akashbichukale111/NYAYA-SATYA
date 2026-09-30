"""
Append-only audit logging. Rows are never updated or deleted by the API —
only inserted. See docs/UNWIND_INTEGRATION.md for the external contract.
"""
import uuid
from sqlalchemy.orm import Session
from models import AuditEvent


def log_event(db: Session, *, case_id: str = None, actor: str = "system", role: str = None,
              event: str, result: str = "ok", correlation_id: str = None,
              source: str = "backend", details: dict = None) -> AuditEvent:
    row = AuditEvent(
        case_id=case_id,
        actor=actor,
        role=role,
        event=event,
        result=result,
        correlation_id=correlation_id or uuid.uuid4().hex[:12],
        source=source,
        details=details or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
