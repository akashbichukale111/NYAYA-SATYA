"""Contradiction detection and discovery metrics.
"""

from __future__ import annotations

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class ContradictionMetrics:
    """Calculates contradiction discovery metrics on CaseDigitalTwin instances."""

    def compute_metrics(
        self,
        twin: CaseDigitalTwin,
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Measure surfaced contradictions."""
        metrics: list[ImpactMetric] = []
        case_id = twin.case_id

        direct_contras = len(twin.contradictions)
        claim_contras = sum(1 for c in twin.claims.values() if c.contradicting_evidence_ids)
        total_contras = direct_contras + claim_contras

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_CONTRA_TOTAL_{case_id}",
                name="Total Contradictions Surfaced",
                category=MetricCategory.EVIDENCE_ANALYSIS,
                classification=classification,
                value=float(total_contras),
                unit="count",
                description="Total contradictory evidence relationships identified and indexed in twin",
            )
        )

        total_claims = len(twin.claims)
        ratio = (claim_contras / total_claims) if total_claims > 0 else 0.0
        metrics.append(
            ImpactMetric(
                metric_id=f"MET_CONTRA_CLAIM_RATIO_{case_id}",
                name="Contradicted Claims Ratio",
                category=MetricCategory.EVIDENCE_ANALYSIS,
                classification=classification,
                value=round(ratio, 4),
                unit="ratio",
                description="Proportion of claims subject to conflicting documentary evidence",
            )
        )

        return metrics
