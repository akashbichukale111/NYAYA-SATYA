from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.evaluation import run_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("")
def evaluation(case_id: str | None = Query(None), db: Session = Depends(get_db)):
    return run_evaluation(db, case_id=case_id)
