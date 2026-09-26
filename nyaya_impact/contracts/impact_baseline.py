"""Baseline vs Treatment comparative measurement contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_impact.contracts.impact_metric import MetricClassification


@dataclass
class BaselineMeasurement:
    """Metrics recorded under simulated manual or standard workflow."""

    baseline_id: str
    case_id: str
    manual_review_time_estimated_minutes: float
    contradictions_manually_found: int
    unsupported_claims_caught: int
    provenance_verified_manually_ratio: float
    manual_fatigue_points: int
    classification: MetricClassification = MetricClassification.ESTIMATED
    notes: str = "Standard manual human advocate preparation baseline."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TreatmentMeasurement:
    """Metrics recorded using NYAYA-SATYA automated structural pipeline."""

    treatment_id: str
    case_id: str
    analysis_execution_time_seconds: float
    contradictions_automatically_surfaced: int
    unsupported_claims_caught: int
    provenance_coverage_ratio: float
    automated_checks_run: int
    human_checkpoints_required: int
    classification: MetricClassification = MetricClassification.OBSERVED
    notes: str = "NYAYA-SATYA pipeline execution."

    @property
    def automated_processing_time_seconds(self) -> float:
        return self.analysis_execution_time_seconds

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["automated_processing_time_seconds"] = self.automated_processing_time_seconds
        return d


@dataclass
class ComparativeTrialResult:
    """Calculated comparison between baseline and treatment."""

    trial_id: str
    case_id: str
    baseline: BaselineMeasurement
    treatment: TreatmentMeasurement
    contradiction_discovery_delta: int
    unsupported_claim_detection_delta: int
    provenance_coverage_delta: float
    automated_to_manual_ratio: float
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "case_id": self.case_id,
            "baseline": self.baseline.to_dict(),
            "treatment": self.treatment.to_dict(),
            "contradiction_discovery_delta": self.contradiction_discovery_delta,
            "unsupported_claim_detection_delta": self.unsupported_claim_detection_delta,
            "provenance_coverage_delta": round(self.provenance_coverage_delta, 4),
            "automated_to_manual_ratio": round(self.automated_to_manual_ratio, 4),
            "notes": self.notes,
        }
