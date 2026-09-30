from sqlalchemy.orm import Session
from app.models.models import AuditEvent


def log_audit(db: Session, *, actor_user_id: str | None, action: str,
              target_type: str | None = None, target_id: str | None = None,
              detail: dict | None = None) -> None:
    """
    Every consequential action (auth, approvals, review decisions, task
    completion overrides, exports) must be recorded here. Audit notifications
    are not user-configurable (see NotificationPreference).
    """
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail_json=detail or {},
    )
    db.add(event)
    db.commit()
