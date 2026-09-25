"""Downstream Impact Analysis for NYAYA-SATYA Case Digital Twin.

Computes which claims, issues, and downstream reasoning dependencies are
destabilized or altered when an evidence item or foundational claim changes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.traversal.claim_dependencies import get_claim_descendants
from nyaya_twin.traversal.evidence_paths import get_evidence_dependent_claims


@dataclass(frozen=True)
class DownstreamImpactReport:
    """Detailed report on the downstream cascade of an evidence or claim change."""

    target_id: str
    target_type: str  # "EVIDENCE" | "CLAIM"
    directly_affected_claims: tuple[str, ...]
    transitively_affected_claims: tuple[str, ...]
    affected_issues: tuple[str, ...]
    affected_events: tuple[str, ...]
    impact_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "directly_affected_claims": list(self.directly_affected_claims),
            "transitively_affected_claims": list(self.transitively_affected_claims),
            "affected_issues": list(self.affected_issues),
            "affected_events": list(self.affected_events),
            "impact_summary": self.impact_summary,
        }


def compute_evidence_invalidation_impact(
    twin: CaseDigitalTwin,
    evidence_id: str,
) -> DownstreamImpactReport:
    """Calculates all downstream claims and issues affected if evidence_id is invalidated."""
    direct_claims = get_evidence_dependent_claims(twin, evidence_id)

    transitive_claims: set[str] = set()
    for cid in direct_claims:
        transitive_claims.update(get_claim_descendants(twin, cid))

    all_affected_claims = set(direct_claims).union(transitive_claims)

    # Find affected issues
    affected_issues: set[str] = set()
    for issue in twin.issues.values():
        if evidence_id in issue.related_evidence_ids or any(
            cid in issue.related_claim_ids for cid in all_affected_claims
        ):
            affected_issues.add(issue.issue_id)

    # Find affected events
    affected_events: set[str] = set()
    for event in twin.events.values():
        if evidence_id in event.source_evidence_ids or any(
            cid in event.related_claim_ids for cid in all_affected_claims
        ):
            affected_events.add(event.event_id)

    total_claims = len(all_affected_claims)
    total_issues = len(affected_issues)
    summary = (
        f"Invalidating evidence {evidence_id} impacts {len(direct_claims)} direct claim(s), "
        f"{len(transitive_claims)} downstream dependent claim(s), and {total_issues} legal issue(s)."
    )

    return DownstreamImpactReport(
        target_id=evidence_id,
        target_type="EVIDENCE",
        directly_affected_claims=tuple(sorted(direct_claims)),
        transitively_affected_claims=tuple(sorted(transitive_claims)),
        affected_issues=tuple(sorted(affected_issues)),
        affected_events=tuple(sorted(affected_events)),
        impact_summary=summary,
    )
