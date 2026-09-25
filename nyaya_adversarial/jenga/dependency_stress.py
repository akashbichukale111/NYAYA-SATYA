"""Evidence Dependency Stress Testing for NYAYA-SATYA.

Stresses multi-hop dependency chains (E -> C1 -> C2 -> C3 -> Issue).
Identifies fragile single points of failure (SPOFs) and maximum cascade depths.
Strictly non-adjudicative: structural dependency stress, not verdict prediction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.traversal.claim_dependencies import get_claim_descendants
from nyaya_twin.traversal.evidence_paths import get_evidence_dependent_claims


@dataclass
class DependencyChainStress:
    """Stress evaluation for an individual dependency chain."""

    root_evidence_id: str
    target_claim_id: str
    chain_path: list[str]
    chain_length: int
    is_single_point_of_failure: bool
    affected_issues: list[str]
    vulnerability_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DependencyStressSummary:
    """Case-wide dependency stress summary."""

    case_id: str
    total_chains_tested: int
    single_points_of_failure: list[str]
    longest_chain_length: int
    high_stress_chains: list[DependencyChainStress] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "total_chains_tested": self.total_chains_tested,
            "single_points_of_failure": self.single_points_of_failure,
            "longest_chain_length": self.longest_chain_length,
            "high_stress_chains": [c.to_dict() for c in self.high_stress_chains],
        }


class DependencyStressEngine:
    """Engine for testing depth and resilience of reasoning dependency chains."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id

    def stress_test_all_chains(self) -> DependencyStressSummary:
        """Evaluates all evidence-to-claim-to-claim chains across the twin."""
        spofs: set[str] = set()
        stress_chains: list[DependencyChainStress] = []
        longest = 0
        total_tested = 0

        for ev_id in self.twin.evidence_refs.keys():
            direct_claims = get_evidence_dependent_claims(self.twin, ev_id)
            for cid in direct_claims:
                total_tested += 1
                descendants = list(get_claim_descendants(self.twin, cid))
                chain = [ev_id, cid] + descendants
                chain_len = len(chain)
                if chain_len > longest:
                    longest = chain_len

                # Check if ev_id is a single point of failure for cid
                claim = self.twin.claims.get(cid)
                is_spof = bool(claim and claim.supporting_evidence_ids == [ev_id])
                if is_spof:
                    spofs.add(ev_id)

                # Check affected issues
                affected_issues = [
                    iss.issue_id for iss in self.twin.issues.values()
                    if cid in iss.related_claim_ids or any(d in iss.related_claim_ids for d in descendants)
                ]

                if is_spof or chain_len >= 3 or affected_issues:
                    stress_chains.append(
                        DependencyChainStress(
                            root_evidence_id=ev_id,
                            target_claim_id=cid,
                            chain_path=chain,
                            chain_length=chain_len,
                            is_single_point_of_failure=is_spof,
                            affected_issues=affected_issues,
                            vulnerability_notes=(
                                f"Root {ev_id} supports {cid} with {len(descendants)} transitive dependents "
                                f"and {len(affected_issues)} issue(s). SPOF: {is_spof}."
                            ),
                        )
                    )

        return DependencyStressSummary(
            case_id=self.case_id,
            total_chains_tested=total_tested,
            single_points_of_failure=sorted(spofs),
            longest_chain_length=longest,
            high_stress_chains=sorted(stress_chains, key=lambda c: (c.is_single_point_of_failure, c.chain_length), reverse=True),
        )
