from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import orm, schemas
from app.core.security import get_current_user, CurrentUser, get_case_or_404, require_min_role, ADMIN_ONLY_MIN_ROLE
from app.agents.time_machine import list_snapshots, take_snapshot, diff_snapshots
from app.agents.simulation import run_simulation, run_crash_test, SUPPORTED_SIMULATION_EVENTS
from app.agents.digital_twin import build_digital_twin
from app.agents.governance import log_audit_event
from app.core.evaluation import run_evaluation_suite

router = APIRouter(prefix="/api/cases", tags=["analysis"])


@router.get("/{case_id}/time-machine")
def get_time_machine(case_id: str, compare_a: str = None, compare_b: str = None,
                      db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    snapshots = list_snapshots(db, case_id)
    snap_summaries = [{"id": s.id, "reason": s.snapshot_reason, "created_at": s.created_at.isoformat()}
                       for s in snapshots]

    result = {"snapshots": snap_summaries}
    if compare_a and compare_b:
        a = next((s for s in snapshots if s.id == compare_a), None)
        b = next((s for s in snapshots if s.id == compare_b), None)
        if not a or not b:
            raise HTTPException(status_code=404, detail="One or both snapshot ids not found for this case")
        result["diff"] = diff_snapshots(a.snapshot_data, b.snapshot_data)
        result["snapshot_a"] = a.snapshot_data
        result["snapshot_b"] = b.snapshot_data
    elif snapshots:
        # default: diff earliest vs latest so the endpoint is useful with no params
        latest_live = build_digital_twin(db, case_id)
        result["diff_earliest_vs_current"] = diff_snapshots(snapshots[0].snapshot_data, latest_live)
    return result


@router.post("/{case_id}/time-machine/snapshot")
def create_snapshot(case_id: str, reason: str = "manual", db: Session = Depends(get_db),
                     user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    snap = take_snapshot(db, case_id, reason, user.user_id)
    return {"id": snap.id, "created_at": snap.created_at.isoformat()}


@router.post("/{case_id}/simulation")
def post_simulation(case_id: str, payload: schemas.SimulationRequest, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    result = run_simulation(db, case_id, payload.event_type, payload.target_entity_id)
    log_audit_event(db, case_id, user.user_id, "SIMULATE", "Simulation", None,
                     {"event_type": payload.event_type, "target": payload.target_entity_id})
    return result


@router.get("/{case_id}/simulation/supported-events")
def get_supported_simulation_events(case_id: str, db: Session = Depends(get_db),
                                     user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    return {"supported_events": SUPPORTED_SIMULATION_EVENTS}


@router.post("/{case_id}/crash-test")
def post_crash_test(case_id: str, payload: schemas.CrashTestRequest, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    result = run_crash_test(db, case_id, payload.event_type, payload.target_entity_id)
    log_audit_event(db, case_id, user.user_id, "CRASH_TEST", "CrashTest", None,
                     {"event_type": payload.event_type, "target": payload.target_entity_id})
    return result


@router.get("/{case_id}/evaluation")
def get_evaluation(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    get_case_or_404(db, case_id)
    return run_evaluation_suite(db, case_id)


@router.get("/{case_id}/integration/nyaya-satya")
def get_integration_adapter(case_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    """
    NYAYA-SATYA integration adapter. Returns the operational summary contract
    from the master spec. This endpoint is independently runnable and does
    not depend on any downstream NYAYA-SATYA module being present.
    """
    get_case_or_404(db, case_id)
    twin = build_digital_twin(db, case_id)
    edges = db.query(orm.Dependency).filter(orm.Dependency.case_id == case_id).all()
    verifications_pending = db.query(orm.ReviewTask).filter(
        orm.ReviewTask.case_id == case_id, orm.ReviewTask.status == "PENDING"
    ).all()
    return {
        "case_id": case_id,
        "custody_state": twin.get("custody_state"),
        "custody_state_confidence": twin.get("custody_state_confidence"),
        "latest_verified_event": twin.get("latest_verified_event"),
        "upcoming_tracked_events": twin.get("upcoming_tracked_events"),
        "attention_items": twin.get("attention_items"),
        "conflicts": twin.get("conflicts"),
        "missing_information": twin.get("missing_information"),
        "verification_pending": [{"id": t.id, "type": t.task_type} for t in verifications_pending],
        "dependency_items": [{"type": e.dependency_type, "status": e.status} for e in edges],
        "provenance_refs": twin.get("provenance_refs"),
        "last_updated": twin.get("last_updated"),
        "disclaimer": "This is an operational tracking summary. It is not a legal conclusion, "
                       "bail determination, or custody-lawfulness assessment.",
    }
