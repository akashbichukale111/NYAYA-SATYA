"""Cryptographic provenance and chain-of-custody metrics.
"""

from __future__ import annotations

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class ProvenanceMetrics:
    """Calculates cryptographic provenance coverage."""

    def compute_metrics(
        self,
        twin: CaseDigitalTwin,
        *,
        classification: MetricClassification = MetricClassification.OBSERVED,
    ) -> list[ImpactMetric]:
        """Compute provenance completeness metrics."""
        metrics: list[ImpactMetric] = []
        case_id = twin.case_id

        total_claims = len(twin.claims)
        claims_with_prov = sum(1 for c in twin.claims.values() if c.provenance_refs)
        coverage = (claims_with_prov / total_claims) if total_claims > 0 else 1.0

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_PROV_COVERAGE_{case_id}",
                name="Provenance Coverage Ratio",
                category=MetricCategory.EVIDENCE_PROCESSING,
                classification=classification,
                value=round(coverage, 4),
                unit="ratio",
                description="Proportion of claims linked to an unbroken SHA-256 provenance chain",
            )
        )

        total_ev = len(twin.evidence_refs)
        clean_ev = sum(
            1 for e in twin.evidence_refs.values()
            if getattr(e, "risk_level", None) and getattr(e.risk_level, "value", str(e.risk_level)) == "CLEAN"
        )
        clean_ratio = (clean_ev / total_ev) if total_ev > 0 else 1.0

        metrics.append(
            ImpactMetric(
                metric_id=f"MET_PROV_CLEAN_EVIDENCE_RATIO_{case_id}",
                name="Sanitized Clean Evidence Ratio",
                category=MetricCategory.EVIDENCE_PROCESSING,
                classification=classification,
                value=round(clean_ratio, 4),
                unit="ratio",
                description="Proportion of ingested evidence verified clean without quarantine triggers",
            )
        )

        return metrics
