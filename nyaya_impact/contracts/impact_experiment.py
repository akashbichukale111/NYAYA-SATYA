"""Impact experiment contracts for NYAYA-SATYA Proven Impact subsystem.

Defines deterministic comparative trial configurations and results.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_impact.contracts.impact_metric import ImpactMetric


@dataclass
class ExperimentResult:
    """Consolidated outcome of an executed comparative trial."""

    experiment_id: str
    sample_count: int
    baseline_metrics: dict[str, float] = field(default_factory=dict)
    treatment_metrics: dict[str, float] = field(default_factory=dict)
    deltas: dict[str, float] = field(default_factory=dict)
    structural_findings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "sample_count": self.sample_count,
            "baseline_metrics": {k: round(v, 4) for k, v in self.baseline_metrics.items()},
            "treatment_metrics": {k: round(v, 4) for k, v in self.treatment_metrics.items()},
            "deltas": {k: round(v, 4) for k, v in self.deltas.items()},
            "structural_findings": list(self.structural_findings),
            "limitations": list(self.limitations),
            "execution_time_seconds": round(self.execution_time_seconds, 2),
        }


@dataclass
class ImpactExperiment:
    """Configuration and execution record of an impact trial."""

    experiment_id: str
    hypothesis: str
    dataset_type: str  # SYNTHETIC, PUBLIC_RECORDS, PRIVATE_EVALUATION
    dataset_version: str
    baseline_definition: str
    treatment_definition: str
    methodology: str
    sample_count: int
    execution_environment: str = "PYTHON_TEST_RUNNER"
    metrics_tracked: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    results: ExperimentResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def reproducibility_fingerprint(self) -> str:
        """Deterministic fingerprint of experiment setup and recorded outcomes."""
        payload = {
            "exp_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "dataset_type": self.dataset_type,
            "dataset_version": self.dataset_version,
            "baseline": self.baseline_definition,
            "treatment": self.treatment_definition,
            "sample_count": self.sample_count,
            "results": self.results.to_dict() if self.results else {},
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "dataset_type": self.dataset_type,
            "dataset_version": self.dataset_version,
            "baseline_definition": self.baseline_definition,
            "treatment_definition": self.treatment_definition,
            "methodology": self.methodology,
            "sample_count": self.sample_count,
            "execution_environment": self.execution_environment,
            "metrics_tracked": list(self.metrics_tracked),
            "limitations": list(self.limitations),
            "results": self.results.to_dict() if self.results else None,
            "reproducibility_fingerprint": self.reproducibility_fingerprint,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
