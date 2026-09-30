from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, StateVersion
from app.state_twin import build_snapshot
from app.freshness import compute_freshness

router = APIRouter(prefix="/api/cases", tags=["state"])


@router.get("/{case_id}/state")
def current_state(case_id: str, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")
    snapshot = build_snapshot(db, case_id)
    freshness = compute_freshness(db, case_id)
    return {
        "case_id": case_id,
        "current_version_number": case.current_version_number,
        "procedural_stage": case.procedural_stage,
        "snapshot": snapshot,
        "freshness": freshness,
    }


@router.get("/{case_id}/versions")
def list_versions(case_id: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    versions = (
        db.query(StateVersion).filter(StateVersion.case_id == case_id)
        .order_by(StateVersion.version_number).all()
    )
    return [
        {"id": v.id, "version_number": v.version_number, "label": v.label,
         "created_at": v.created_at.isoformat(), "triggering_event_id": v.triggering_event_id,
         "freshness": v.freshness}
        for v in versions
    ]


@router.get("/{case_id}/versions/{version_number}")
def get_version(case_id: str, version_number: int, db: Session = Depends(get_db)):
    v = (
        db.query(StateVersion)
        .filter(StateVersion.case_id == case_id, StateVersion.version_number == version_number)
        .first()
    )
    if not v:
        raise HTTPException(404, "version not found")
    return {
        "id": v.id, "version_number": v.version_number, "label": v.label,
        "created_at": v.created_at.isoformat(), "triggering_event_id": v.triggering_event_id,
        "freshness": v.freshness, "snapshot": v.snapshot,
    }
