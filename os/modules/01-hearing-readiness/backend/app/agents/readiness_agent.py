"""Readiness Agent -- INVESTIGATE + VERIFY at the requirement level, runs
the full deterministic readiness audit (recomputes every requirement's
status from currently-linked evidence)."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.services import readiness_engine


class ReadinessAgent(Agent):
    name = "readiness_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:
        snapshot = readiness_engine.run_readiness_audit(db, case_id)
        return StepResult(
            step="INVESTIGATE", agent=self.name, tool_calls=["requirement_check"],
            status="OK", detail=snapshot,
        )
