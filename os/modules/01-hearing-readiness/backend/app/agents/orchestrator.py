"""
Orchestrates the agentic loop (section 10):
OBSERVE -> UNDERSTAND -> INVESTIGATE -> VERIFY -> IDENTIFY BLOCKER ->
PLAN SAFE ACTION -> REQUEST APPROVAL -> [human approves elsewhere] ->
EXECUTE -> VERIFY RESULT -> UPDATE STATE -> REASSESS

run_readiness_pass() performs everything up to REQUEST APPROVAL
automatically (nothing consequential happens without a human yet).
run_post_approval_pass() performs EXECUTE..REASSESS for one approved
action. Both persist an AgentRun trace.
"""
from __future__ import annotations

import uuid

from app.models.agent_run import AgentRun
from app.agents.intake_agent import IntakeAgent
from app.agents.case_state_agent import CaseStateAgent
from app.agents.hearing_context_agent import HearingContextAgent
from app.agents.readiness_agent import ReadinessAgent
from app.agents.blocker_investigation_agent import BlockerInvestigationAgent
from app.agents.evidence_verification_agent import EvidenceVerificationAgent
from app.agents.action_planning_agent import ActionPlanningAgent
from app.agents.verification_agent import VerificationAgent
from app.agents.audit_agent import AuditAgent


def run_readiness_pass(db, case_id: str) -> AgentRun:
    correlation_id = uuid.uuid4().hex[:12]
    run = AgentRun(case_id=case_id, correlation_id=correlation_id, status="RUNNING", steps=[])
    db.add(run)
    db.flush()

    steps = []
    for agent in (IntakeAgent(), CaseStateAgent(), HearingContextAgent(),
                  ReadinessAgent(), BlockerInvestigationAgent(),
                  EvidenceVerificationAgent(), ActionPlanningAgent()):
        result = agent.run(db, case_id)
        steps.append(result.to_dict())
        if result.status == "FAILED":
            run.status = "FAILED"
            run.steps = steps
            db.flush()
            return run

    summary = {"steps_completed": len(steps)}
    audit_result = AuditAgent().run(db, case_id, correlation_id=correlation_id, summary=summary)
    steps.append(audit_result.to_dict())

    run.status = "COMPLETED"
    run.steps = steps
    db.flush()
    return run


def run_post_approval_pass(db, case_id: str, action_id: str) -> AgentRun:
    """EXECUTE approved action -> VERIFY -> UPDATE STATE (re-audit) -> REASSESS."""
    correlation_id = uuid.uuid4().hex[:12]
    run = AgentRun(case_id=case_id, correlation_id=correlation_id, status="RUNNING", steps=[])
    db.add(run)
    db.flush()

    steps = []
    verify_result = VerificationAgent().run(db, case_id, action_id=action_id)
    steps.append(verify_result.to_dict())

    if verify_result.status == "BLOCKED":
        run.status = "FAILED"
        run.steps = steps
        db.flush()
        return run

    # UPDATE STATE + REASSESS: re-run the readiness agent so blockers/state
    # reflect the just-verified action.
    readiness_result = ReadinessAgent().run(db, case_id)
    readiness_result.step = "REASSESS"
    steps.append(readiness_result.to_dict())

    summary = {"action_id": action_id, "verification_status": verify_result.status}
    audit_result = AuditAgent().run(db, case_id, correlation_id=correlation_id, summary=summary)
    steps.append(audit_result.to_dict())

    run.status = "COMPLETED"
    run.steps = steps
    db.flush()
    return run
