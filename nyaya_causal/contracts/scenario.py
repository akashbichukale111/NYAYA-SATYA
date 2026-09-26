"""Counterfactual scenario container contracts for NYAYA-SATYA.

Each scenario packages an intervention, its preconditions, execution config,
results, comparison, provenance, and integrity hash.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_causal.contracts.comparison import CounterfactualComparison
from nyaya_causal.contracts.counterfactual import BlastRadiusReport
from nyaya_causal.contracts.intervention import Intervention
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class ScenarioStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INCONSISTENT = "INCONSISTENT"


@dataclass
class CounterfactualScenario:
    """A complete counterfactual scenario package."""

    scenario_id: str
    case_id: str
    base_twin_version: int
    intervention: Intervention
    preconditions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    execution_config: dict[str, Any] = field(default_factory=dict)
    blast_radius: BlastRadiusReport | None = None
    comparison: CounterfactualComparison | None = None
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    status: ScenarioStatus = ScenarioStatus.CREATED
    error_message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def integrity_hash(self) -> str:
        """Deterministic hash of the full scenario specification."""
        payload = {
            "scenario_id": self.scenario_id,
            "case_id": self.case_id,
            "base_twin_version": self.base_twin_version,
            "intervention_hash": self.intervention.scenario_hash,
            "preconditions": sorted(self.preconditions),
            "assumptions": sorted(self.assumptions),
        }
        return compute_sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "case_id": self.case_id,
            "base_twin_version": self.base_twin_version,
            "intervention": self.intervention.to_dict(),
            "preconditions": self.preconditions,
            "assumptions": self.assumptions,
            "execution_config": self.execution_config,
            "blast_radius": self.blast_radius.to_dict() if self.blast_radius else None,
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "status": self.status.value,
            "error_message": self.error_message,
            "integrity_hash": self.integrity_hash,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
        }
