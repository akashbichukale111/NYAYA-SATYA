from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import orm, schemas
from app.core.security import get_current_user, CurrentUser, get_case_or_404, require_min_role, WRITE_MIN_ROLE
from app.agents.reconciliation import run_all_reconciliation
from app.agents.attention import run_attention_engine
from app.agents.dependency import rebuild_dependency_graph
from app.agents.governance import log_audit_event
from app.agents.time_machine import take_snapshot

router = APIRouter(prefix="/api/cases", tags=["manual-events"])


@router.post("/{case_id}/custody-events/manual")
def add_manual_custody_event(case_id: str, payload: schemas.ManualCustodyEventCreate,
                              db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    require_min_role(user, WRITE_MIN_ROLE)
    get_case_or_404(db, case_id)
    event = orm.CustodyEvent(
        case_id=case_id, event_type=payload.event_type, event_date=payload.event_date,
        date_type=payload.date_type, verification_status="USER_REPORTED",
        reported_by_user_id=user.user_id, notes=payload.notes,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    log_audit_event(db, case_id, user.user_id, "CREATE", "CustodyEvent", event.id,
                     {"event_type": event.event_type, "reported_by": user.user_id})
    run_all_reconciliation(db, case_id)
    run_attention_engine(db, case_id)
    rebuild_dependency_graph(db, case_id)
    db.commit()
    take_snapshot(db, case_id, "manual_event_added", user.user_id)
    return {"id": event.id, "status": "recorded", "verification_status": event.verification_status}
