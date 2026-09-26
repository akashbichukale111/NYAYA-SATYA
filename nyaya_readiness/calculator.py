"""Readiness calculator for NYAYA-SATYA.

Computes structural readiness snapshots and deltas across pre-repair and post-repair states.
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_readiness.readiness_delta import CaseReadinessDelta
from nyaya_readiness.readiness_snapshot import CaseReadinessSnapshot
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus


class ReadinessCalculator:
    """Calculates structural preparedness without outcome probabilities."""

    def compute_snapshot(
        self,
        twin: CaseDigitalTwin,
        *,
        reattack_findings_count: int = 0,
        repair_immunity_status: str = "UNKNOWN",
        perturbation_stability_score: float = 1.0,
        unresolved_assumptions_count: int = 0,
    ) -> CaseReadinessSnapshot:
        """Evaluate structural metrics for a given CaseDigitalTwin state."""
        total_claims = len(twin.claims)
        claims_with_evidence = sum(
            1 for c in twin.claims.values()
            if c.supporting_evidence_ids or c.status == ClaimStatus.SUPPORTED
        )
        evidence_coverage = (
            claims_with_evidence / total_claims if total_claims > 0 else 1.0
        )

        unsupported_count = sum(
            1 for c in twin.claims.values()
            if not c.supporting_evidence_ids or c.status == ClaimStatus.UNSUPPORTED
        )

        unresolved_contradictions = len(twin.contradictions)
        for c in twin.claims.values():
            if c.contradicting_evidence_ids:
                unresolved_contradictions += 1

        # Provenance coverage
        claims_with_prov = sum(1 for c in twin.claims.values() if c.provenance_refs)
        provenance_coverage = claims_with_prov / total_claims if total_claims > 0 else 1.0

        # Causal dependency coverage: dependencies with supported prerequisites
        dep_rels = [
            r for r in twin.relationships.values()
            if r.relationship_type.value == "DEPENDS_ON"
        ]
        if dep_rels:
            supported_deps = sum(
                1 for r in dep_rels
                if r.target_id in twin.claims and twin.claims[r.target_id].supporting_evidence_ids
            )
            causal_coverage = supported_deps / len(dep_rels)
        else:
            causal_coverage = 1.0

        # Human review obligations: unresolved contradictions + unsupported assertions
        human_obligations = unsupported_count + unresolved_contradictions + reattack_findings_count

        return CaseReadinessSnapshot(
            case_id=twin.case_id,
            snapshot_id=f"SNAP_{uuid.uuid4().hex[:8]}",
            total_claims=total_claims,
            claims_with_evidence=claims_with_evidence,
            evidence_coverage_ratio=round(evidence_coverage, 4),
            unresolved_contradictions_count=unresolved_contradictions,
            provenance_coverage_ratio=round(provenance_coverage, 4),
            authority_verification_ratio=0.8,
            evidence_gaps_count=unsupported_count,
            causal_dependency_coverage_ratio=round(causal_coverage, 4),
            unresolved_assumptions_count=unresolved_assumptions_count,
            unsupported_assertions_count=unsupported_count,
            reattack_findings_count=reattack_findings_count,
            repair_immunity_status=repair_immunity_status,
            perturbation_stability_score=round(perturbation_stability_score, 4),
            human_review_obligations_count=human_obligations,
            twin_integrity_hash=twin.integrity_hash,
        )

    def compute_delta(
        self,
        repair_id: str,
        pre_snapshot: CaseReadinessSnapshot,
        post_snapshot: CaseReadinessSnapshot,
    ) -> CaseReadinessDelta:
        """Compare two snapshots to produce the structural delta."""
        ev_delta = post_snapshot.evidence_coverage_ratio - pre_snapshot.evidence_coverage_ratio
        contra_delta = post_snapshot.unresolved_contradictions_count - pre_snapshot.unresolved_contradictions_count
        unsup_delta = post_snapshot.unsupported_assertions_count - pre_snapshot.unsupported_assertions_count
        prov_delta = post_snapshot.provenance_coverage_ratio - pre_snapshot.provenance_coverage_ratio
        auth_delta = post_snapshot.authority_verification_ratio - pre_snapshot.authority_verification_ratio
        assump_delta = post_snapshot.unresolved_assumptions_count - pre_snapshot.unresolved_assumptions_count

        regressions = max(0, contra_delta) + max(0, unsup_delta)
        net_progress = (ev_delta >= 0) and (contra_delta <= 0) and (unsup_delta <= 0) and (regressions == 0)

        changes: list[str] = []
        if ev_delta > 0:
            changes.append(f"Evidence coverage improved by +{ev_delta * 100:.1f}%")
        if unsup_delta < 0:
            changes.append(f"Unsupported assertions reduced by {abs(unsup_delta)}")
        if contra_delta < 0:
            changes.append(f"Contradictions reduced by {abs(contra_delta)}")
        if regressions > 0:
            changes.append(f"WARNING: {regressions} regressions detected in post-repair state")

        review_obligations: list[str] = []
        if post_snapshot.human_review_obligations_count > 0:
            review_obligations.append(
                f"{post_snapshot.human_review_obligations_count} items remain for Human Legal Gate review"
            )

        return CaseReadinessDelta(
            case_id=pre_snapshot.case_id,
            repair_id=repair_id,
            pre_snapshot=pre_snapshot,
            post_snapshot=post_snapshot,
            evidence_coverage_delta=ev_delta,
            contradictions_delta=contra_delta,
            unsupported_claims_delta=unsup_delta,
            unresolved_assumptions_delta=assump_delta,
            provenance_coverage_delta=prov_delta,
            authority_verification_delta=auth_delta,
            regressions_count=regressions,
            net_structural_progress=net_progress,
            summary_of_changes=changes,
            human_review_obligations=review_obligations,
        )
