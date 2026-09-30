from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.seed_demo import seed_all_demo_cases, DEMO_MARKER

router = APIRouter(tags=["demo"])


@router.post("/api/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Idempotent: seeds exactly the 3 synthetic demo cases if they don't
    already exist, and returns their ids. Never seeds into a case that
    isn't flagged is_demo=True."""
    case_ids = seed_all_demo_cases(db)
    return {"marker": DEMO_MARKER, "demo_case_ids": case_ids}


@router.get("/api/demo/marker")
def get_marker():
    return {"marker": DEMO_MARKER}
