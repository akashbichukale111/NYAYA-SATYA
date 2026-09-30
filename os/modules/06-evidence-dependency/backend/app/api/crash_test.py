from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rbac import Actor, get_actor
from app.core.case_access import require_case_with_access
from app.models.orm import EvidenceItem
from app.services.impact_service import run_crash_test
from app.schemas.schemas import CrashTestRequest

router = APIRouter()


@router.post("/evidence/{evidence_id}/crash-test")
def crash_test_evidence(evidence_id: str, payload: CrashTestRequest, db: Session = Depends(get_db),
                         actor: Actor = Depends(get_actor)):
    item = db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    require_case_with_access(db, item.case_id, actor)
    run = run_crash_test(
        db, item.case_id, payload.event_type, payload.target_type or "EVIDENCE", evidence_id,
        created_by=f"USER_SIMULATION:{actor.user_id}",
    )
    return {
        "id": run.id, "case_id": run.case_id, "event_type": run.event_type,
        "target_type": run.target_type, "target_id": run.target_id,
        "before_state": run.before_state, "after_state": run.after_state,
        "affected_claims": run.affected_claims, "affected_issues": run.affected_issues,
        "new_gaps": run.new_gaps, "new_conflicts": run.new_conflicts,
        "criticality": run.criticality, "human_review_required": run.human_review_required,
        "note": "SIMULATION ONLY -- no case data was modified.",
    }
