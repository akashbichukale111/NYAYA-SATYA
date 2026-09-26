"""Re-attack and repair immunity metrics.
"""

from __future__ import annotations

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification
from nyaya_reattack.repair_immunity import RepairImmunityAssessment, RepairImmunityStatus


class ReAttackMetrics:
    """Calculates independent re-attack and immunity metrics."""

    def compute_metrics(
        self,
        case_id: str,
        assessments: list[RepairImmunityAssessment],
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Compute repair immunity rates."""
        metrics: list[ImpactMetric] = []

        total_assessed = len(assessments)
        immune_count = sum(1 for a in assessments if a.status == RepairImmunityStatus.IMMUNE)
        regression_count = sum(1 for a in assessments if a.status == RepairImmunityStatus.REGRESSION)

        immunity_rate = (immune_count / total_assessed) if total_assessed > 0 else 0.0

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REATK_IMMUNITY_RATE_{case_id}",
                name="Repair Immunity Rate",
                category=MetricCategory.REATTACK,
                classification=classification,
                value=round(immunity_rate, 4),
                unit="ratio",
                description="Proportion of repairs that survived independent re-attack without new vulnerabilities",
            )
        )

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REATK_REGRESSION_COUNT_{case_id}",
                name="Repair Regressions Detected",
                category=MetricCategory.REATTACK,
                classification=classification,
                value=float(regression_count),
                unit="count",
                description="Number of repair attempts that induced new vulnerabilities or side-effects",
            )
        )

        return metrics
