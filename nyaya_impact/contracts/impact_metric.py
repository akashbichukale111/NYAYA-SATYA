"""Impact metric contracts for NYAYA-SATYA Proven Impact subsystem.

Defines verifiable structural metrics and strictly requires categorical labeling
(OBSERVED vs SYNTHETIC vs ESTIMATED vs PRIVATE_EVALUATION vs REAL_DEPLOYMENT).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MetricCategory(str, Enum):
    """Broad domain of the measured structural metric."""

    EVIDENCE_PROCESSING = "EVIDENCE_PROCESSING"
    EVIDENCE_ANALYSIS = "EVIDENCE_ANALYSIS"
    ADVERSARIAL_ANALYSIS = "ADVERSARIAL_ANALYSIS"
    REPAIR = "REPAIR"
    REATTACK = "REATTACK"
    READINESS = "READINESS"
    WORKFLOW = "WORKFLOW"


class MetricClassification(str, Enum):
    """Epistemic provenance of the metric value.

    Guarantees no synthetic simulation is deceptively presented as real-world impact.
    """

    OBSERVED = "OBSERVED"
    SYNTHETIC = "SYNTHETIC"
    ESTIMATED = "ESTIMATED"
    PRIVATE_EVALUATION = "PRIVATE_EVALUATION"
    REAL_DEPLOYMENT = "REAL_DEPLOYMENT"


# Epistemic classification alias
EpistemicStatus = MetricClassification


@dataclass
class ImpactMetric:
    """A quantified, reproducible structural metric."""

    metric_id: str
    name: str
    category: MetricCategory
    classification: MetricClassification
    value: float
    unit: str  # count, ratio, ms, percent
    description: str
    baseline_value: float | None = None
    treatment_value: float | None = None
    delta_value: float | None = None
    source_provenance_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.metric_id:
            raise ValueError("metric_id cannot be blank")
        if not self.name:
            raise ValueError("name cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "category": self.category.value,
            "classification": self.classification.value,
            "value": round(self.value, 4),
            "unit": self.unit,
            "description": self.description,
            "baseline_value": round(self.baseline_value, 4) if self.baseline_value is not None else None,
            "treatment_value": round(self.treatment_value, 4) if self.treatment_value is not None else None,
            "delta_value": round(self.delta_value, 4) if self.delta_value is not None else None,
            "source_provenance_hash": self.source_provenance_hash,
            "metadata": self.metadata,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImpactMetric:
        d = dict(data)
        if isinstance(d.get("category"), str):
            d["category"] = MetricCategory(d["category"])
        if isinstance(d.get("classification"), str):
            d["classification"] = MetricClassification(d["classification"])
        return cls(**d)
