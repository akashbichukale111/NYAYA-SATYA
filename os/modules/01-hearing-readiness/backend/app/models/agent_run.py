from __future__ import annotations

from sqlalchemy import Column, String, ForeignKey, JSON
from app.db import Base
from app.models.mixins import TimestampMixin, gen_id


class AgentRun(Base, TimestampMixin):
    """Trace of one orchestrator pass through the OBSERVE..REASSESS loop."""
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=lambda: gen_id("run"))
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    correlation_id = Column(String, nullable=False)
    steps = Column(JSON, default=list)  # [{step, agent, tool_calls, duration_ms, status}]
    status = Column(String, nullable=False, default="RUNNING")  # RUNNING/COMPLETED/FAILED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "correlation_id": self.correlation_id,
            "steps": self.steps,
            "status": self.status,
        }
