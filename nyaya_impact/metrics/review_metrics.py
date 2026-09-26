"""Human review obligations and checklist metrics.
"""

from __future__ import annotations

from nyaya_dossier.human_checklist import HumanReviewChecklist, ReviewStatus
from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification


class ReviewMetrics:
    """Calculates human review metrics from HumanReviewChecklist."""

    def compute_metrics(
        self,
        checklist: HumanReviewChecklist,
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Compute metrics on human review obligations."""
        metrics: list[ImpactMetric] = []
        case_id = checklist.case_id

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REV_TOTAL_ITEMS_{case_id}",
                name="Total Human Review Checkpoints",
                category=MetricCategory.WORKFLOW,
                classification=classification,
                value=float(checklist.total_count),
                unit="count",
                description="Total discrete structural review items formulated for human legal review",
            )
        )

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REV_CRITICAL_ITEMS_{case_id}",
                name="Critical Review Obligations",
                category=MetricCategory.WORKFLOW,
                classification=classification,
                value=float(checklist.critical_count),
                unit="count",
                description="High-urgency items (e.g. unresolved evidentiary contradictions)",
            )
        )

        resolved_ratio = (checklist.resolved_count / checklist.total_count) if checklist.total_count > 0 else 1.0
        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REV_RESOLVED_RATIO_{case_id}",
                name="Human Review Resolution Ratio",
                category=MetricCategory.WORKFLOW,
                classification=classification,
                value=round(resolved_ratio, 4),
                unit="ratio",
                description="Proportion of human review obligations that have received definitive jurist decisions",
            )
        )

        return metrics
