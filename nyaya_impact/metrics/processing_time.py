"""Processing duration and throughput metrics.
"""

from __future__ import annotations

from nyaya_impact.collection.event_collector import EventCollector
from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification


class ProcessingTimeMetrics:
    """Calculates processing durations from recorded events."""

    def compute_metrics(
        self,
        case_id: str,
        collector: EventCollector,
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Compute latency metrics for the case."""
        metrics: list[ImpactMetric] = []
        events = collector.get_events_for_case(case_id)

        total_ms = sum(e.duration_ms for e in events)
        metrics.append(
            ImpactMetric(
                metric_id=f"MET_DUR_TOTAL_{case_id}",
                name="Total Pipeline Duration",
                category=MetricCategory.WORKFLOW,
                classification=classification,
                value=round(total_ms, 2),
                unit="ms",
                description="Total execution latency recorded across all analytical phases",
            )
        )

        # Average phase latency
        if events:
            avg_ms = total_ms / len(events)
            metrics.append(
                ImpactMetric(
                    metric_id=f"MET_DUR_AVG_PHASE_{case_id}",
                    name="Average Phase Duration",
                    category=MetricCategory.WORKFLOW,
                    classification=classification,
                    value=round(avg_ms, 2),
                    unit="ms",
                    description="Average latency per analytical workflow step",
                )
            )

        return metrics
