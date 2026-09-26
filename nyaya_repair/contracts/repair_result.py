"""Repair execution and simulation result contracts for NYAYA-SATYA Auto-Healer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.contracts.repair_utility import RepairUtilityVector


@dataclass
class RepairExecutionResult:
    """Outcome of applying a repair candidate to a twin simulation copy."""

    repair_id: str
    case_id: str
    success: bool
    actions_executed: int
    mutated_claim_ids: list[str] = field(default_factory=list)
    mutated_event_ids: list[str] = field(default_factory=list)
    mutated_relationship_ids: list[str] = field(default_factory=list)
    error_message: str | None = None
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "repair_id": self.repair_id,
            "case_id": self.case_id,
            "success": self.success,
            "actions_executed": self.actions_executed,
            "mutated_claim_ids": self.mutated_claim_ids,
            "mutated_event_ids": self.mutated_event_ids,
            "mutated_relationship_ids": self.mutated_relationship_ids,
            "error_message": self.error_message,
            "executed_at": self.executed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairExecutionResult:
        d = dict(data)
        if isinstance(d.get("executed_at"), str):
            d["executed_at"] = datetime.fromisoformat(d["executed_at"])
        return cls(**d)


@dataclass
class SimulatedRepairReport:
    """Comprehensive analysis report of a simulated repair candidate."""

    report_id: str
    case_id: str
    repair_candidate: RepairCandidate
    pre_repair_hash: str
    post_repair_hash: str
    execution_result: RepairExecutionResult
    utility_vector: RepairUtilityVector
    blast_radius: dict[str, Any] = field(default_factory=dict)
    re_attack_summary: dict[str, Any] = field(default_factory=dict)
    immunity_status: str = "UNKNOWN"
    is_acceptable: bool = False
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "case_id": self.case_id,
            "repair_candidate": self.repair_candidate.to_dict(),
            "pre_repair_hash": self.pre_repair_hash,
            "post_repair_hash": self.post_repair_hash,
            "execution_result": self.execution_result.to_dict(),
            "utility_vector": self.utility_vector.to_dict(),
            "blast_radius": self.blast_radius,
            "re_attack_summary": self.re_attack_summary,
            "immunity_status": self.immunity_status,
            "is_acceptable": self.is_acceptable,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimulatedRepairReport:
        d = dict(data)
        if "repair_candidate" in d:
            d["repair_candidate"] = RepairCandidate.from_dict(d["repair_candidate"])
        if "execution_result" in d:
            d["execution_result"] = RepairExecutionResult.from_dict(d["execution_result"])
        if "utility_vector" in d:
            d["utility_vector"] = RepairUtilityVector.from_dict(d["utility_vector"])
        if isinstance(d.get("generated_at"), str):
            d["generated_at"] = datetime.fromisoformat(d["generated_at"])
        return cls(**d)
