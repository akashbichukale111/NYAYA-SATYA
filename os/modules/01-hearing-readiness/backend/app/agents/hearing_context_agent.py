"""Hearing Context Agent -- determines/refreshes next-hearing purpose."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.services import case_twin


class HearingContextAgent(Agent):
    name = "hearing_context_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        hearing = case_twin.refresh_hearing_context(db, case_id)
        if hearing is None:
            return StepResult(step="UNDERSTAND", agent=self.name, status="UNKNOWN",
                               detail={"message": "No upcoming hearing on record for this case."})
        return StepResult(
            step="UNDERSTAND", agent=self.name, tool_calls=["hearing_lookup"],
            status="OK" if hearing.purpose_status == "DETERMINED" else "UNCERTAIN",
            detail={"purpose": hearing.purpose, "purpose_status": hearing.purpose_status,
                    "uncertainty_reasons": hearing.uncertainty_reasons},
        )
