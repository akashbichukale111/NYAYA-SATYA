"""Next-Best-Evidence Ranking Engine for NYAYA-SATYA.

Ranks missing evidence candidates by their structural potential to reduce uncertainty.
NON-ADJUDICATION: Presents candidates as priorities for uncertainty reduction,
never as mandatory legal actions or case outcome predictors.
"""

from __future__ import annotations

from typing import Any

from nyaya_adversarial.contracts.missing_evidence import MissingEvidenceCandidate
from nyaya_adversarial.contracts.voi import NextBestEvidence
from nyaya_adversarial.missing.detector import MissingEvidenceDetector
from nyaya_adversarial.missing.uncertainty_reduction import UncertaintyReductionEngine
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class NextBestEvidenceEngine:
    """Ranks missing evidence candidates to prioritize uncertainty reduction."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id
        self.detector = MissingEvidenceDetector(twin)
        self.voi_engine = UncertaintyReductionEngine(twin)

    def rank_next_best_evidence(
        self,
        candidates: list[MissingEvidenceCandidate] | None = None,
    ) -> list[NextBestEvidence]:
        """Evaluates and ranks evidence candidates by structural information value."""
        cands = candidates if candidates is not None else self.detector.detect_missing_evidence()
        evaluated: list[NextBestEvidence] = []

        for cand in cands:
            iv = self.voi_engine.evaluate_information_value(cand)

            affected_issues: list[str] = []
            if cand.related_issue:
                affected_issues.append(cand.related_issue)
            for iss in self.twin.issues.values():
                if any(cid in iss.related_claim_ids for cid in cand.related_claims) and iss.issue_id not in affected_issues:
                    affected_issues.append(iss.issue_id)

            explanation = (
                f"Priority {iv.rating.value}: Addressing '{cand.question}' could reduce uncertainty "
                f"across {len(cand.related_claims)} claim(s) and {len(affected_issues)} issue(s). "
                f"Structural score: {iv.score}."
            )

            evaluated.append(
                NextBestEvidence(
                    candidate_id=cand.candidate_id,
                    question_resolved=cand.question,
                    affected_claims=cand.related_claims,
                    affected_issues=affected_issues,
                    expected_uncertainty_reduction=iv.uncertainty_reduction,
                    dependency_coverage=cand.dependency,
                    acquisition_constraints=cand.access_constraint,
                    confidence=0.85,
                    information_value=iv,
                    explanation=explanation,
                    priority_rank=1,  # will be updated after sorting
                )
            )

        # Sort strictly by information value score descending
        # If two candidates have identical or similar scores, preserve both without discarding
        sorted_candidates = sorted(evaluated, key=lambda e: e.information_value.score, reverse=True)

        # Assign ranks
        for rank, item in enumerate(sorted_candidates, start=1):
            item.priority_rank = rank

        return sorted_candidates
