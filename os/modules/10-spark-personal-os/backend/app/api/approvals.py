from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import User, ApprovalRequest
from app.schemas.schemas import ApprovalRequestOut, ApprovalDecision
from app.core.security import get_current_user
from app.services.access import authorized_case_ids
from app.services.audit import log_audit

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRequestOut])
def my_approvals(case_id: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = authorized_case_ids(db, user)
    if not ids:
        return []
    q = db.query(ApprovalRequest).filter(ApprovalRequest.case_id.in_(ids))
    if case_id:
        q = q.filter(ApprovalRequest.case_id == case_id)
    return q.order_by(ApprovalRequest.created_at.desc()).all()


@router.post("/{approval_id}/decide", response_model=ApprovalRequestOut)
def decide_approval(
    approval_id: str, payload: ApprovalDecision,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    approval = db.get(ApprovalRequest, approval_id)
    ids = authorized_case_ids(db, user)
    if approval is None or approval.case_id not in ids:
        raise HTTPException(status_code=404, detail="Approval request not found")

    approval.status = payload.status
    approval.decided_by = user.id
    approval.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)
    log_audit(db, actor_user_id=user.id, action=f"approval.{payload.status.value}",
              target_type="ApprovalRequest", target_id=approval.id,
              detail={"action_type": approval.action_type.value})
    return approval
