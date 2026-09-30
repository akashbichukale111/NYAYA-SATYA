from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case
from app.graph import build_graph

router = APIRouter(prefix="/api/cases", tags=["graph"])


@router.get("/{case_id}/graph")
def get_graph(case_id: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    return build_graph(db, case_id)
