"""Case State Agent -- confirms/loads the current Case Digital Twin state.
Does not compute readiness itself; that is the Readiness Agent's job."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.services import case_twin


class CaseStateAgent(Agent):
    name = "case_state_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        full = case_twin.get_case_full(db, case_id)
        return StepResult(
            step="UNDERSTAND", agent=self.name, tool_calls=["case_state_lookup"],
            status="OK" if full else "FAILED",
            detail={"requirement_count": len(full["requirements"])} if full else None,
        )
