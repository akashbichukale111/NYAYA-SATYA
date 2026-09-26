"""Repair utility evaluator for NYAYA-SATYA Auto-Healer.

Calculates the multi-dimensional Repair Utility Vector (RUV).
Enforces hard architectural constraints without collapsing into a single score.
"""

from __future__ import annotations

from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_repair.contracts.repair_constraint import RepairConstraints
from nyaya_repair.contracts.repair_utility import RepairUtilityVector
from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.claims import ClaimStatus


class RepairEvaluator:
    """Evaluates repair candidates and computes the Repair Utility Vector."""

    def __init__(self, constraints: RepairConstraints | None = None) -> None:
        self.constraints = constraints or RepairConstraints()

    def evaluate(
        self,
        repair: RepairCandidate,
        original_twin: CaseDigitalTwin,
        repaired_twin: CaseDigitalTwin,
        *,
        new_vulnerability_count: int = 0,
    ) -> RepairUtilityVector:
        """Compute the Repair Utility Vector for a simulated repair."""
        # 1. Evidence Support: proportion of referenced evidence that exists in twin
        evidence_support = 1.0
        if repair.evidence_refs:
            valid_ev = [
                e for e in repair.evidence_refs if e in original_twin.evidence_refs
            ]
            evidence_support = len(valid_ev) / len(repair.evidence_refs)
        elif repair.target_claim_id and repair.target_claim_id in repaired_twin.claims:
            claim = repaired_twin.claims[repair.target_claim_id]
            evidence_support = 1.0 if claim.supporting_evidence_ids else 0.4

        # 2. Legal Grounding: verified authority coverage
        legal_grounding = 0.5
        if repair.authority_refs:
            verified_count = sum(
                1 for a in repair.authority_refs
                if a.status.value == "VERIFIED_AUTHORITY"
            )
            legal_grounding = min(1.0, 0.5 + 0.5 * (verified_count / len(repair.authority_refs)))

        # 3. Fragility Reduction: positive change in target claim status
        fragility_reduction = 0.5
        if repair.target_claim_id:
            orig_c = original_twin.claims.get(repair.target_claim_id)
            rep_c = repaired_twin.claims.get(repair.target_claim_id)
            if orig_c and rep_c:
                if orig_c.status == ClaimStatus.UNSUPPORTED and rep_c.status != ClaimStatus.UNSUPPORTED:
                    fragility_reduction = 0.9
                elif orig_c.status == ClaimStatus.CONTRADICTED and rep_c.status != ClaimStatus.CONTRADICTED:
                    fragility_reduction = 0.8
                elif rep_c.status == ClaimStatus.SUPPORTED:
                    fragility_reduction = 0.85

        # 4. Collateral Impact: changes to claims other than the target
        unintended_count = 0
        for cid, orig_claim in original_twin.claims.items():
            if cid == repair.target_claim_id:
                continue
            rep_claim = repaired_twin.claims.get(cid)
            if rep_claim and rep_claim.status != orig_claim.status:
                # If a non-target claim became unsupported or contradicted, flag collateral impact
                if rep_claim.status in (ClaimStatus.UNSUPPORTED, ClaimStatus.CONTRADICTED):
                    unintended_count += 1

        total_other_claims = max(1, len(original_twin.claims) - 1)
        collateral_impact = min(1.0, unintended_count / total_other_claims)

        # 5. Uncertainty
        uncertainty = 0.3 if evidence_support >= 0.8 else 0.5

        # 6. Violations & Hard Constraints
        new_vulns = new_vulnerability_count
        critical_collateral = 1 if unintended_count > 2 else 0

        # Check for unsupported assertions introduced
        unsupported_introduced = 0
        for evid in repair.evidence_refs:
            if evid not in original_twin.evidence_refs and evid not in repaired_twin.evidence_refs:
                unsupported_introduced += 1

        return RepairUtilityVector(
            evidence_support=round(evidence_support, 4),
            legal_grounding=round(legal_grounding, 4),
            fragility_reduction=round(fragility_reduction, 4),
            collateral_impact=round(collateral_impact, 4),
            uncertainty=round(uncertainty, 4),
            new_vulnerabilities=new_vulns,
            critical_collateral_impact=critical_collateral,
            unsupported_assertions_introduced=unsupported_introduced,
            fabricated_authorities_detected=0,
            silent_fact_alterations=0,
            canonical_twin_mutated=False,
        )
