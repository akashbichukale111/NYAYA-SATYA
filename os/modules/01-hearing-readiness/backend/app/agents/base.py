from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    step: str
    agent: str
    tool_calls: list[str] = field(default_factory=list)
    status: str = "OK"
    detail: Any = None

    def to_dict(self) -> dict:
        return {
            "step": self.step, "agent": self.agent, "tool_calls": self.tool_calls,
            "status": self.status, "detail": self.detail,
        }


class Agent:
    name: str = "base_agent"

    def run(self, db, case_id: str, **kwargs) -> StepResult:  # pragma: no cover - interface
        raise NotImplementedError
