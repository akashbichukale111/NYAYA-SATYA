from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.evaluation_lab import run_evaluation_suite
from app import models

router = APIRouter(tags=["evaluation"])


@router.post("/api/evaluation/run")
def run_evaluation(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Runs the deterministic evaluation suite right now, in this
    process, against fresh isolated evaluation cases it creates and
    leaves in place (marked is_demo=True, titled 'EVAL: ...') for
    inspection. Every result reflects a real assertion that actually
    executed in this request — never a cached or hardcoded value."""
    return run_evaluation_suite(db)
