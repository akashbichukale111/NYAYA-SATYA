from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, Deadline
from app.schemas.schemas import DeadlineOut
from app.core.security import get_current_user
from app.services.access import authorized_case_ids

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


@router.get("", response_model=list[DeadlineOut])
def my_deadlines(case_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids:
        return []
    q = db.query(Deadline).filter(Deadline.case_id.in_(ids))
    if case_id:
        q = q.filter(Deadline.case_id == case_id)
    return q.order_by(Deadline.tracked_date.asc()).all()
