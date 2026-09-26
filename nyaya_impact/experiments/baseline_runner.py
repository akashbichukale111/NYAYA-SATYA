"""Baseline measurement runner simulating manual review workflow.
"""

from __future__ import annotations

import uuid
from nyaya_impact.contracts.impact_baseline import BaselineMeasurement
from nyaya_impact.contracts.impact_metric import MetricClassification
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class BaselineRunner:
    """Simulates baseline manual document inspection parameters."""

    def run_baseline(
        self,
        twin: CaseDigitalTwin,
        *,
        estimated_minutes_per_evidence: float = 15.0,
    ) -> BaselineMeasurement:
        """Estimate manual review parameters based on case complexity."""
        total_ev = len(twin.evidence_refs)
        total_claims = len(twin.claims)
        estimated_minutes = max(30.0, total_ev * estimated_minutes_per_evidence)

        # Baseline estimates typical manual discovery rates without automated graph traversal
        return BaselineMeasurement(
            baseline_id=f"BASE_{uuid.uuid4().hex[:8]}",
            case_id=twin.case_id,
            manual_review_time_estimated_minutes=estimated_minutes,
            contradictions_manually_found=max(0, len(twin.contradictions) - 1),
            unsupported_claims_caught=max(0, sum(1 for c in twin.claims.values() if not c.supporting_evidence_ids) - 1),
            provenance_verified_manually_ratio=0.5,
            manual_fatigue_points=int(total_ev * 2 + total_claims),
            classification=MetricClassification.ESTIMATED,
            notes="Estimated unassisted manual evidence inspection baseline.",
        )
