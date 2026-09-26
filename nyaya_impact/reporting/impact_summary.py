"""Executive impact summary generator for NYAYA-SATYA Proven Impact subsystem.

Provides high-level KPI summaries strictly tagged with epistemic classifications.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nyaya_impact.contracts.impact_baseline import ComparativeTrialResult
from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricClassification
from nyaya_impact.contracts.impact_report import ProvenImpactReport


@dataclass
class ExecutiveKPIs:
    """High-level executive metrics for legal operations leadership."""

    case_or_dataset_id: str
    automated_contradiction_discovery_count: int
    unsupported_claims_caught_count: int
    provenance_coverage_ratio: float
    automated_validation_latency_seconds: float
    human_review_items_pending: int
    epistemic_classification: str = MetricClassification.OBSERVED.value
    notes: str = "Honest structural metrics; no outcome predictions."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ImpactSummaryGenerator:
    """Generates concise executive summaries from impact reports and trial data."""

    def summarize(
        self,
        report: ProvenImpactReport,
        comparative_trial: ComparativeTrialResult | None = None,
    ) -> ExecutiveKPIs:
        """Extract high-level KPIs from a ProvenImpactReport."""
        contra_count = 0
        unsup_count = 0
        prov_ratio = 1.0
        proc_time = 0.0

        for m in report.sec06_metrics:
            if "contradiction" in m.metric_id.lower() or "contra" in m.metric_id.lower():
                if isinstance(m.value, (int, float)):
                    contra_count = max(contra_count, int(m.value))
            elif "unsupported" in m.metric_id.lower() or "gap" in m.metric_id.lower():
                if isinstance(m.value, (int, float)):
                    unsup_count = max(unsup_count, int(m.value))
            elif "coverage" in m.metric_id.lower() or "provenance" in m.metric_id.lower():
                if isinstance(m.value, (int, float)):
                    prov_ratio = float(m.value)
            elif "duration" in m.metric_id.lower() or "latency" in m.metric_id.lower() or "time" in m.metric_id.lower():
                if isinstance(m.value, (int, float)):
                    proc_time = float(m.value)

        if comparative_trial and comparative_trial.treatment:
            contra_count = comparative_trial.treatment.contradictions_automatically_surfaced
            unsup_count = comparative_trial.treatment.unsupported_claims_caught
            prov_ratio = comparative_trial.treatment.provenance_coverage_ratio
            proc_time = comparative_trial.treatment.automated_processing_time_seconds

        return ExecutiveKPIs(
            case_or_dataset_id=report.case_or_dataset_id,
            automated_contradiction_discovery_count=contra_count,
            unsupported_claims_caught_count=unsup_count,
            provenance_coverage_ratio=prov_ratio,
            automated_validation_latency_seconds=proc_time,
            human_review_items_pending=len(report.sec14_open_issues),
            epistemic_classification=(
                report.sec11_deployment_evidence.get(
                    "epistemic_classification", MetricClassification.SYNTHETIC.value
                )
            ),
            notes="Honest structural metrics; zero fabricated numbers or outcome predictions.",
        )
