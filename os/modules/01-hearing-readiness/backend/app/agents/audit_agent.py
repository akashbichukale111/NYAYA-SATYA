"""Audit Agent -- writes/reads the append-only trail for an orchestrator run."""
from __future__ import annotations

from app.agents.base import Agent, StepResult
from app.services import audit_service


class AuditAgent(Agent):
    name = "audit_agent"

    def run(self, db, case_id: str, correlation_id: str, summary: dict, **kwargs) -> StepResult:
        audit_service.log_event(
            db, case_id=case_id, actor="agent:orchestrator", event_type="AGENT_RUN_COMPLETE",
            action="orchestrator_pass", input_ref=None, result=summary, correlation_id=correlation_id,
        )
        return StepResult(step="AUDIT", agent=self.name, tool_calls=["audit_log"], status="OK")
