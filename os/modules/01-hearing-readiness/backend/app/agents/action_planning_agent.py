"""Action Planning Agent -- PLAN SAFE ACTION + REQUEST APPROVAL. Proposes
one safe action per OPEN blocker that doesn't already have a pending/active
action, and leaves them PENDING_APPROVAL -- it never auto-approves."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.models.blocker import Blocker
from app.models.action import Action
from app.services import action_planner


class ActionPlanningAgent(Agent):
    name = "action_planning_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        blockers = db.query(Blocker).filter(Blocker.case_id == case_id, Blocker.status == "OPEN").all()
        proposed = []
        for b in blockers:
            existing = (
                db.query(Action)
                .filter(Action.blocker_id == b.id, Action.status.in_(
                    ["PENDING_APPROVAL", "APPROVED", "EXECUTED", "VERIFIED"]))
                .first()
            )
            if existing:
                continue
            action = action_planner.propose_action(db, b)
            proposed.append(action.id)
        return StepResult(
            step="PLAN_SAFE_ACTION", agent=self.name, tool_calls=["draft_action"],
            status="OK", detail={"proposed_action_ids": proposed, "awaiting_human_approval": True},
        )
