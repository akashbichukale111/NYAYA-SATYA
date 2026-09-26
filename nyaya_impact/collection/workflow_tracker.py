"""Workflow tracker distinguishing automated checks from human review checkpoints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class WorkflowStats:
    """Summary of workflow checkpoints executed."""

    case_id: str
    automated_checks_run: int = 0
    manual_checkpoints_required: int = 0
    manual_decisions_made: int = 0
    total_phases_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkflowTracker:
    """Tracks progression of cases through automated checks and manual checkpoints."""

    def __init__(self) -> None:
        self._stats: dict[str, WorkflowStats] = {}

    def get_or_create(self, case_id: str) -> WorkflowStats:
        if case_id not in self._stats:
            self._stats[case_id] = WorkflowStats(case_id=case_id)
        return self._stats[case_id]

    def record_automated_check(self, case_id: str, count: int = 1) -> None:
        stats = self.get_or_create(case_id)
        stats.automated_checks_run += count

    def record_manual_checkpoint(self, case_id: str, count: int = 1) -> None:
        stats = self.get_or_create(case_id)
        stats.manual_checkpoints_required += count

    def record_manual_decision(self, case_id: str, count: int = 1) -> None:
        stats = self.get_or_create(case_id)
        stats.manual_decisions_made += count

    def record_phase_completed(self, case_id: str) -> None:
        stats = self.get_or_create(case_id)
        stats.total_phases_completed += 1

    def reset_for_test(self) -> None:
        self._stats.clear()
