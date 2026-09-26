"""Repair engine candidate, acceptance, and utility metrics.
"""

from __future__ import annotations

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification
from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.contracts.repair_result import SimulatedRepairReport


class RepairMetrics:
    """Calculates metrics over generated and simulated repair candidates."""

    def compute_metrics(
        self,
        case_id: str,
        candidates: list[RepairCandidate],
        simulated_reports: list[SimulatedRepairReport],
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Compute repair generation and simulation metrics."""
        metrics: list[ImpactMetric] = []

        total_gen = len(candidates)
        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REP_TOTAL_GEN_{case_id}",
                name="Repair Candidates Generated",
                category=MetricCategory.REPAIR,
                classification=classification,
                value=float(total_gen),
                unit="count",
                description="Total structured repair candidates proposed for detected vulnerabilities",
            )
        )

        sim_count = len(simulated_reports)
        acceptable_count = sum(1 for r in simulated_reports if r.is_acceptable)
        acc_ratio = (acceptable_count / sim_count) if sim_count > 0 else 0.0

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_REP_ACCEPTABLE_RATIO_{case_id}",
                name="Simulated Repair Acceptance Ratio",
                category=MetricCategory.REPAIR,
                classification=classification,
                value=round(acc_ratio, 4),
                unit="ratio",
                description="Proportion of simulated repairs satisfying all hard constraints and utility thresholds",
            )
        )

        return metrics
