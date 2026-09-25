"""Jenga Fragility Engine for NYAYA-SATYA.

Simulates the targeted removal or challenging of evidence and claim nodes one at a time.
Observes what downstream claims, issues, and dependencies collapse.
STRICT IMMUTABILITY: Never mutates canonical CaseDigitalTwin.
NON-ADJUDICATION: Uses bounded deterministic structural scores, not win probabilities.
"""

from __future__ import annotations

import copy
from typing import Any

from nyaya_adversarial.contracts.fragility import (
    FragilityReport,
    StructuralFragilityScore,
    StructuralSeverity,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin, compute_twin_hash
from nyaya_twin.traversal.claim_dependencies import get_claim_descendants
from nyaya_twin.traversal.downstream_impact import compute_evidence_invalidation_impact
from nyaya_twin.traversal.evidence_paths import get_evidence_dependent_claims


class JengaFragilityEngine:
    """Engine simulating discrete node removals to measure structural fragility."""

    def __init__(self, canonical_twin: CaseDigitalTwin) -> None:
        self._canonical_twin = canonical_twin
        self.case_id = canonical_twin.case_id

    def analyze_evidence_fragility(self, evidence_id: str) -> FragilityReport:
        """Simulates removal of evidence_id and calculates its structural fragility."""
        initial_hash = compute_twin_hash(self._canonical_twin)

        # 1. Direct and indirect dependents
        direct_claims = list(get_evidence_dependent_claims(self._canonical_twin, evidence_id))
        indirect_claims: set[str] = set()
        for cid in direct_claims:
            indirect_claims.update(get_claim_descendants(self._canonical_twin, cid))
        all_affected_claims = sorted(set(direct_claims) | indirect_claims)

        # 2. Check single-source reliance & unsupported claims
        single_source_claims: list[str] = []
        unsupported_claims: list[str] = []
        for cid in all_affected_claims:
            claim = self._canonical_twin.claims.get(cid)
            if not claim:
                continue
            # If evidence_id is the ONLY supporting evidence
            if claim.supporting_evidence_ids == [evidence_id]:
                single_source_claims.append(cid)
                unsupported_claims.append(cid)
            elif evidence_id in claim.supporting_evidence_ids and len(claim.supporting_evidence_ids) == 1:
                single_source_claims.append(cid)
                unsupported_claims.append(cid)

        # 3. Check unresolved issues
        affected_issues: set[str] = set()
        for issue in self._canonical_twin.issues.values():
            if evidence_id in issue.related_evidence_ids or any(cid in issue.related_claim_ids for cid in all_affected_claims):
                affected_issues.add(issue.issue_id)

        # 4. Check contradiction exposure
        contradictions_count = sum(
            1 for c in self._canonical_twin.contradictions
            if c.evidence_a_id == evidence_id or c.evidence_b_id == evidence_id
        )

        # 5. Check provenance gaps
        ref = self._canonical_twin.evidence_refs.get(evidence_id)
        prov_gaps = 0
        if not ref or not getattr(ref, "provenance_refs", []):
            prov_gaps = 1

        # 6. Calculate deterministic StructuralFragilityScore [0.0, 1.0]
        breadth = len(direct_claims)
        depth = len(indirect_claims)
        breadth_factor = min(breadth * 0.15, 0.35)
        depth_factor = min(depth * 0.1, 0.25)
        single_src_factor = 0.25 if single_source_claims else 0.0
        contra_factor = min(contradictions_count * 0.1, 0.15)
        prov_factor = 0.1 if prov_gaps > 0 else 0.0

        raw_score = breadth_factor + depth_factor + single_src_factor + contra_factor + prov_factor
        score = min(max(round(raw_score, 3), 0.0), 1.0)

        explanation = (
            f"Evidence {evidence_id} removal impacts {breadth} direct claim(s) and {depth} transitive descendant(s). "
            f"{len(single_source_claims)} claim(s) rely solely on this node. "
            f"Contradiction count: {contradictions_count}, Provenance gaps: {prov_gaps}."
        )

        fragility_score = StructuralFragilityScore(
            score=score,
            dependency_breadth=breadth,
            dependency_depth=depth,
            single_source_reliance=len(single_source_claims) > 0,
            contradiction_exposure=contradictions_count,
            provenance_gaps=prov_gaps,
            unsupported_downstream_claims=len(unsupported_claims),
            explanation=explanation,
        )

        # Ensure canonical twin is unmodified
        final_hash = compute_twin_hash(self._canonical_twin)
        if initial_hash != final_hash:
            raise RuntimeError("IMMUTABILITY VIOLATION: CaseDigitalTwin mutated during Jenga simulation!")

        return FragilityReport(
            target_id=evidence_id,
            target_type="EVIDENCE",
            direct_dependents=direct_claims,
            indirect_dependents=sorted(indirect_claims),
            unsupported_claim_count=len(unsupported_claims),
            unresolved_issue_count=len(affected_issues),
            contradiction_count=contradictions_count,
            provenance_gaps=prov_gaps,
            single_source_dependencies=single_source_claims,
            assumptions_exposed=[],
            structural_fragility=fragility_score,
            explanation=explanation,
            provenance_refs=getattr(ref, "provenance_refs", []) if ref else [],
        )

    def analyze_claim_fragility(self, claim_id: str) -> FragilityReport:
        """Simulates challenging or invalidating a claim."""
        initial_hash = compute_twin_hash(self._canonical_twin)
        claim = self._canonical_twin.claims.get(claim_id)
        if not claim:
            raise ValueError(f"Claim {claim_id} not found in case {self.case_id}")

        descendants = list(get_claim_descendants(self._canonical_twin, claim_id))
        breadth = len(descendants)
        depth = 1 if descendants else 0

        # Check issues affected
        affected_issues = [
            iss.issue_id for iss in self._canonical_twin.issues.values()
            if claim_id in iss.related_claim_ids or any(d in iss.related_claim_ids for d in descendants)
        ]

        single_source = len(claim.supporting_evidence_ids) == 1
        raw_score = min(0.2 + (0.15 * breadth) + (0.2 if single_source else 0.0), 1.0)
        score = round(raw_score, 3)

        explanation = (
            f"Claim {claim_id} supports {breadth} downstream dependent claim(s) and impacts {len(affected_issues)} issue(s). "
            f"Single-source evidence reliance: {single_source}."
        )

        fragility_score = StructuralFragilityScore(
            score=score,
            dependency_breadth=breadth,
            dependency_depth=depth,
            single_source_reliance=single_source,
            contradiction_exposure=len(claim.contradicting_evidence_ids),
            provenance_gaps=0,
            unsupported_downstream_claims=breadth,
            explanation=explanation,
        )

        final_hash = compute_twin_hash(self._canonical_twin)
        if initial_hash != final_hash:
            raise RuntimeError("IMMUTABILITY VIOLATION: CaseDigitalTwin mutated during Jenga claim analysis!")

        return FragilityReport(
            target_id=claim_id,
            target_type="CLAIM",
            direct_dependents=descendants[:breadth],
            indirect_dependents=descendants,
            unsupported_claim_count=breadth,
            unresolved_issue_count=len(affected_issues),
            contradiction_count=len(claim.contradicting_evidence_ids),
            provenance_gaps=0,
            single_source_dependencies=claim.supporting_evidence_ids if single_source else [],
            assumptions_exposed=[],
            structural_fragility=fragility_score,
            explanation=explanation,
            provenance_refs=list(claim.provenance_refs),
        )

    def analyze_all_evidence(self) -> list[FragilityReport]:
        """Runs Jenga fragility analysis across all evidence nodes in the twin."""
        reports: list[FragilityReport] = []
        for ev_id in self._canonical_twin.evidence_refs.keys():
            reports.append(self.analyze_evidence_fragility(ev_id))
        return sorted(reports, key=lambda r: r.structural_fragility.score, reverse=True)
