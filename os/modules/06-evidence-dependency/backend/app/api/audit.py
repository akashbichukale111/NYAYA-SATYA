from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import AuditEvent

router = APIRouter()


@router.get("/cases/{case_id}/audit")
def get_audit(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.created_at.desc())
        .all()
    )
    return [
        {
            "id": e.id, "actor": e.actor, "actor_type": e.actor_type, "action": e.action,
            "target_type": e.target_type, "target_id": e.target_id, "detail": e.detail,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
