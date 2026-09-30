"""Verification Agent -- EXECUTE APPROVED ACTION + VERIFY RESULT. Only
runs for actions that already have an APPROVE decision on record; the
tool registry additionally enforces this at the state_update tool level."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.models.action import Action
from app.services import verification_engine


class VerificationAgent(Agent):
    name = "verification_agent"

    def run(self, db, case_id: str, action_id: str, **kwargs) -> StepResult:
        action = db.query(Action).filter(Action.id == action_id, Action.case_id == case_id).first()
        if not action:
            return StepResult(step="EXECUTE", agent=self.name, status="FAILED",
                               detail={"error": "action not found"})
        if not action.approval or action.approval.decision != "APPROVE":
            return StepResult(step="EXECUTE", agent=self.name, status="BLOCKED",
                               detail={"error": "action has not been approved"})

        verification_engine.execute_action(db, action)
        verification = verification_engine.verify_action(db, action)
        return StepResult(
            step="VERIFY_RESULT", agent=self.name, tool_calls=["state_update", "verification"],
            status=verification.result,
            detail={"action_id": action.id, "verification": verification.to_dict()},
        )
