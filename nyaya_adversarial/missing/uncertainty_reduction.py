"""Value-of-Information (VoI) Foundation for NYAYA-SATYA.

Calculates transparent, explainable structural Information Value scores
measuring potential uncertainty reduction across the case.
NON-ADJUDICATION GUARANTEE: Never uses monetary or legal win probability optimization.
"""

from __future__ import annotations

from nyaya_adversarial.contracts.missing_evidence import MissingEvidenceCandidate
from nyaya_adversarial.contracts.voi import (
    InformationValueBreakdown,
    InformationValueRating,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class UncertaintyReductionEngine:
    """Engine computing structural Value-of-Information for candidate evidence items."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id

    def evaluate_information_value(
        self,
        candidate: MissingEvidenceCandidate,
    ) -> InformationValueBreakdown:
        """Evaluates structural information value of discovering or requesting candidate evidence."""
        # 1. Claims affected
        claims_affected_count = len(candidate.related_claims)

        # 2. Issues affected
        issues_affected_count = 1 if candidate.related_issue else 0
        if not issues_affected_count and candidate.related_claims:
            # Count issues governing any affected claim
            for iss in self.twin.issues.values():
                if any(cid in iss.related_claim_ids for cid in candidate.related_claims):
                    issues_affected_count += 1

        # 3. Contradiction resolution potential
        # Check if any affected claim is linked to contradictions
        contradiction_potential = 0
        for cand in self.twin.contradictions:
            for cid in candidate.related_claims:
                claim = self.twin.claims.get(cid)
                if claim and (cand.evidence_a_id in claim.supporting_evidence_ids or cand.evidence_b_id in claim.supporting_evidence_ids):
                    contradiction_potential += 1
                    break

        # 4. Dependency centrality
        total_claims = max(len(self.twin.claims), 1)
        centrality = min(round((claims_affected_count + len(candidate.dependency)) / total_claims, 3), 1.0)

        # 5. Potential uncertainty reduction
        uncertainty_reduction = round(candidate.current_uncertainty * 0.75, 2)

        # 6. Structural composite score [0.0, 1.0]
        score_val = (
            (uncertainty_reduction * 0.3)
            + (min(claims_affected_count * 0.15, 0.3))
            + (min(issues_affected_count * 0.15, 0.2))
            + (min(contradiction_potential * 0.1, 0.2))
        )
        score = min(max(round(score_val, 3), 0.0), 1.0)

        # Rating determination
        if score >= 0.75 or contradiction_potential >= 2 or issues_affected_count >= 2:
            rating = InformationValueRating.CRITICAL
        elif score >= 0.50 or claims_affected_count >= 2:
            rating = InformationValueRating.HIGH
        elif score >= 0.25:
            rating = InformationValueRating.MEDIUM
        else:
            rating = InformationValueRating.LOW

        explanation = (
            f"Information Value {rating.value} (score={score}): "
            f"Potential to reduce uncertainty by {uncertainty_reduction} across "
            f"{claims_affected_count} claim(s), {issues_affected_count} issue(s), "
            f"and resolve {contradiction_potential} contradiction(s)."
        )

        return InformationValueBreakdown(
            rating=rating,
            score=score,
            uncertainty_reduction=uncertainty_reduction,
            claims_affected_count=claims_affected_count,
            issues_affected_count=issues_affected_count,
            contradiction_resolution_potential=contradiction_potential,
            dependency_centrality=centrality,
            acquisition_cost="LOW",
            acquisition_difficulty="MODERATE" if "SUBPOENA" in candidate.access_constraint else "EASY",
            explanation=explanation,
        )
