from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, StateVersion, StateChange

router = APIRouter(prefix="/api/cases", tags=["changes"])


@router.get("/{case_id}/changes")
def what_changed(case_id: str, db: Session = Depends(get_db)):
    """
    "What Changed?" mode (section 15): summarizes the diff between the two
    most recent state versions, with each item linking back to its source
    event via source_event_id (VIEW SOURCES in the UI).
    """
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "case not found")

    versions = (
        db.query(StateVersion).filter(StateVersion.case_id == case_id)
        .order_by(StateVersion.version_number.desc()).limit(2).all()
    )
    if len(versions) < 2:
        return {"case_id": case_id, "message": "Only one state version exists; nothing to compare yet.",
                "changes": []}

    latest, previous = versions[0], versions[1]
    changes = (
        db.query(StateChange)
        .filter(StateChange.case_id == case_id, StateChange.to_version == latest.version_number)
        .all()
    )
    return {
        "case_id": case_id,
        "from_version": previous.version_number,
        "to_version": latest.version_number,
        "changes": [
            {
                "id": c.id, "category": c.category, "entity_type": c.entity_type, "entity_id": c.entity_id,
                "before": c.before, "after": c.after, "reason": c.reason, "source_event_id": c.source_event_id,
            }
            for c in changes
        ],
    }
