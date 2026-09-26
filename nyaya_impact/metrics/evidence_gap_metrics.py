"""Evidence gap and unsupported assertions metrics.
"""

from __future__ import annotations

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus


class EvidenceGapMetrics:
    """Calculates evidence gap metrics on CaseDigitalTwin instances."""

    def compute_metrics(
        self,
        twin: CaseDigitalTwin,
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Compute unsupported assertions and missing evidence counts."""
        metrics: list[ImpactMetric] = []
        case_id = twin.case_id

        unsupported_count = sum(
            1 for c in twin.claims.values()
            if not c.supporting_evidence_ids or c.status == ClaimStatus.UNSUPPORTED
        )
        total_claims = len(twin.claims)
        gap_ratio = (unsupported_count / total_claims) if total_claims > 0 else 0.0

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_GAP_UNSUP_COUNT_{case_id}",
                name="Unsupported Assertions Identified",
                category=MetricCategory.EVIDENCE_ANALYSIS,
                classification=classification,
                value=float(unsupported_count),
                unit="count",
                description="Number of factual/legal assertions lacking documentary or oral corroboration",
            )
        )

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_GAP_UNSUP_RATIO_{case_id}",
                name="Unsupported Claims Ratio",
                category=MetricCategory.EVIDENCE_ANALYSIS,
                classification=classification,
                value=round(gap_ratio, 4),
                unit="ratio",
                description="Proportion of total claims in the twin without evidentiary backing",
            )
        )

        return metrics
