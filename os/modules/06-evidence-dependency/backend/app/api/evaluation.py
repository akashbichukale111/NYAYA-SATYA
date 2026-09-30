from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.services.evaluation_service import run_evaluation_suite

router = APIRouter()


@router.get("/cases/{case_id}/evaluation")
def get_evaluation(case_id: str, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    require_case_with_access(db, case_id, actor)
    return run_evaluation_suite(db, case_id)
