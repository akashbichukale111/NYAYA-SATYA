from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import Issue
from app.schemas.schemas import IssueCreate, IssueOut
from app.services.review_service import log_audit_event

router = APIRouter()


@router.post("/cases/{case_id}/issues", response_model=IssueOut)
def create_issue(case_id: str, payload: IssueCreate, db: Session = Depends(get_db),
                  actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    issue = Issue(case_id=case_id, question=payload.question, description=payload.description)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    log_audit_event(db, case_id, actor=actor.user_id, actor_type="USER", action="ISSUE_CREATED",
                     target_type="ISSUE", target_id=issue.id)
    db.commit()
    return issue


@router.get("/cases/{case_id}/issues", response_model=list[IssueOut])
def list_issues(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return db.query(Issue).filter(Issue.case_id == case_id).all()


@router.get("/issues/{issue_id}", response_model=IssueOut)
def get_issue(issue_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_case_with_access(db, issue.case_id, actor)
    return issue
