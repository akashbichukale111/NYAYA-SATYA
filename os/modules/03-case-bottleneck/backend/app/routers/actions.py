from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import ActionItem, ActionStatus, Case, VerificationRecord, utcnow
from ..schemas import RejectRequest
from ..agents.verification import execute_action, VerificationAgent
from ..agents.reassessment import ReassessmentAgent
from .. import audit

router = APIRouter(prefix="/api/cases", tags=["actions"])


@router.get("/{case_id}/actions")
def list_actions(case_id: str, session: Session = Depends(get_session)):
    _require_case(session, case_id)
    return session.exec(select(ActionItem).where(ActionItem.case_id == case_id)).all()


@router.post("/{case_id}/actions/{action_id}/approve")
def approve_action(case_id: str, action_id: str, session: Session = Depends(get_session)):
    action = _require_action(session, case_id, action_id)
    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(409, f"Action is in status {action.status.value}, not eligible for approval.")

    correlation_id = audit.new_correlation_id()
    action.status = ActionStatus.APPROVED
    action.approved_at = utcnow()
    session.add(action)
    session.commit()
    audit.record(session, case_id=case_id, correlation_id=correlation_id, actor="human",
                 event="ACTION_APPROVED", source="human_gate", result={"action_id": action_id})

    case = session.get(Case, case_id)
    action = execute_action(session, action, case.demo_scenario if case else None)
    audit.record(session, case_id=case_id, correlation_id=correlation_id, actor="action-executor",
                 event="ACTION_EXECUTED", source="agent", result={"action_id": action_id, "result": action.result})

    record: VerificationRecord = VerificationAgent().verify(session, action)
    audit.record(session, case_id=case_id, correlation_id=correlation_id, actor=VerificationAgent.name,
                 event="ACTION_VERIFIED" if record.passed else "ACTION_VERIFICATION_FAILED", source="agent",
                 result={"action_id": action_id, "passed": record.passed, "details": record.details})

    reassessment = ReassessmentAgent().run(session, action, record.passed)
    audit.record(session, case_id=case_id, correlation_id=correlation_id, actor="reassessment-agent",
                 event="REASSESSMENT_COMPLETED", source="agent", result=reassessment)

    session.refresh(action)
    return {
        "action": action,
        "verification": record,
        "newly_visible_bottlenecks": reassessment["newly_visible_bottlenecks"],
    }


@router.post("/{case_id}/actions/{action_id}/reject")
def reject_action(case_id: str, action_id: str, body: RejectRequest, session: Session = Depends(get_session)):
    action = _require_action(session, case_id, action_id)
    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(409, f"Action is in status {action.status.value}, not eligible for rejection.")
    action.status = ActionStatus.REJECTED
    action.rejection_reason = body.reason
    session.add(action)
    session.commit()
    session.refresh(action)
    audit.record(session, case_id=case_id, correlation_id=audit.new_correlation_id(), actor="human",
                 event="ACTION_REJECTED", source="human_gate", result={"action_id": action_id, "reason": body.reason})
    return action


def _require_case(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


def _require_action(session: Session, case_id: str, action_id: str) -> ActionItem:
    action = session.get(ActionItem, action_id)
    if not action or action.case_id != case_id:
        raise HTTPException(404, "Action not found for this case")
    return action
