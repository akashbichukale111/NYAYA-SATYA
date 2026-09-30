from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.action import Action, Approval
from app.services import (
    simulation_engine, crash_test_engine, time_machine, audit_service,
)
from app.agents.orchestrator import run_post_approval_pass
from app.schemas.api_schemas import (
    SimulateRequest, CrashTestRequest, ApprovalDecision,
)

router = APIRouter(prefix="/api/cases", tags=["ops"])


# --- Simulation ---------------------------------------------------------

@router.post("/{case_id}/simulate")
def simulate(case_id: str, payload: SimulateRequest, db: Session = Depends(get_db)):
    record = simulation_engine.simulate(db, case_id, payload.hypothesis)
    db.commit()
    return record.to_dict()


# --- Crash test ----------------------------------------------------------

@router.post("/{case_id}/crash-test")
def crash_test(case_id: str, payload: CrashTestRequest, db: Session = Depends(get_db)):
    if payload.mutation:
        try:
            record = crash_test_engine.run_crash_test(db, case_id, payload.mutation)
            db.commit()
            return record.to_dict()
        except ValueError as e:
            raise HTTPException(400, str(e))
    records = crash_test_engine.run_all_crash_tests(db, case_id)
    db.commit()
    return [r.to_dict() for r in records]


@router.get("/{case_id}/crash-test")
def list_crash_tests(case_id: str, db: Session = Depends(get_db)):
    from app.models.crash_test import CrashTest
    records = db.query(CrashTest).filter(CrashTest.case_id == case_id).order_by(CrashTest.created_at.desc()).all()
    return [r.to_dict() for r in records]


# --- Time Machine --------------------------------------------------------

@router.get("/{case_id}/versions")
def list_versions(case_id: str, db: Session = Depends(get_db)):
    return time_machine.list_versions(db, case_id)


@router.get("/{case_id}/versions/diff")
def diff_versions(case_id: str, from_version: int, to_version: int, db: Session = Depends(get_db)):
    try:
        return time_machine.diff_versions(db, case_id, from_version, to_version)
    except ValueError as e:
        raise HTTPException(404, str(e))


# --- Actions / Human approval gate ---------------------------------------

@router.get("/{case_id}/actions")
def list_actions(case_id: str, db: Session = Depends(get_db)):
    actions = db.query(Action).filter(Action.case_id == case_id).order_by(Action.created_at.desc()).all()
    return [a.to_dict() for a in actions]


@router.post("/{case_id}/actions/{action_id}/approve")
def approve_action(case_id: str, action_id: str, payload: ApprovalDecision, db: Session = Depends(get_db)):
    action = db.query(Action).filter(Action.id == action_id, Action.case_id == case_id).first()
    if not action:
        raise HTTPException(404, "Action not found")
    if payload.decision not in ("APPROVE", "EDIT", "REJECT"):
        raise HTTPException(400, "decision must be APPROVE, EDIT, or REJECT")

    approval = Approval(
        action_id=action.id, decision=payload.decision, approved_by=payload.approved_by,
        edited_description=payload.edited_description, notes=payload.notes,
    )
    db.add(approval)

    if payload.decision == "REJECT":
        action.status = "REJECTED"
    elif payload.decision == "EDIT":
        action.status = "EDITED"
        if payload.edited_description:
            action.description = payload.edited_description
    else:
        action.status = "APPROVED"
    db.flush()

    audit_service.log_event(
        db, case_id=case_id, actor=f"user:{payload.approved_by}", event_type="APPROVAL_DECISION",
        action=f"decision={payload.decision}", input_ref={"action_id": action_id},
        result={"status": action.status}, correlation_id=action.id,
    )
    db.commit()

    agent_run = None
    if payload.decision == "APPROVE":
        agent_run = run_post_approval_pass(db, case_id, action_id)
        db.commit()
        db.refresh(action)  # pick up status/result changes made during execution+verification

    result = {"action": action.to_dict(), "approval": approval.to_dict()}
    if agent_run is not None:
        result["agent_run"] = agent_run.to_dict()

    return result


# --- Audit ----------------------------------------------------------------

@router.get("/{case_id}/audit")
def get_audit(case_id: str, db: Session = Depends(get_db)):
    return audit_service.get_case_audit(db, case_id)
