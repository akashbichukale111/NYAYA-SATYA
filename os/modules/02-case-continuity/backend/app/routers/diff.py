from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Case, StateVersion
from app.diff import diff_snapshots

router = APIRouter(prefix="/api/cases", tags=["diff"])


@router.get("/{case_id}/diff")
def diff_versions(
    case_id: str,
    from_version: int = Query(..., alias="from"),
    to_version: int = Query(..., alias="to"),
    db: Session = Depends(get_db),
):
    if not db.get(Case, case_id):
        raise HTTPException(404, "case not found")
    v_from = db.query(StateVersion).filter(
        StateVersion.case_id == case_id, StateVersion.version_number == from_version).first()
    v_to = db.query(StateVersion).filter(
        StateVersion.case_id == case_id, StateVersion.version_number == to_version).first()
    if not v_from or not v_to:
        raise HTTPException(404, "one or both versions not found")
    return {
        "case_id": case_id, "from_version": from_version, "to_version": to_version,
        "diff": diff_snapshots(v_from.snapshot, v_to.snapshot),
    }
