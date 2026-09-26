"""Attack comparison engine for NYAYA-SATYA Re-Attack subsystem.

Compares pre-repair adversarial findings against post-repair re-attack findings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nyaya_adversarial.contracts.result import AdversarialFinding


@dataclass
class AttackComparisonReport:
    """Comparison of adversarial stress findings before and after repair."""

    pre_repair_finding_count: int
    post_repair_finding_count: int
    resolved_findings: list[str] = field(default_factory=list)
    persisting_findings: list[str] = field(default_factory=list)
    new_findings: list[str] = field(default_factory=list)
    net_improvement: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pre_repair_finding_count": self.pre_repair_finding_count,
            "post_repair_finding_count": self.post_repair_finding_count,
            "resolved_findings": list(self.resolved_findings),
            "persisting_findings": list(self.persisting_findings),
            "new_findings": list(self.new_findings),
            "net_improvement": self.net_improvement,
        }


class AttackComparator:
    """Compares pre-repair vs post-repair adversarial results."""

    def compare(
        self,
        pre_findings: list[AdversarialFinding],
        post_findings: list[AdversarialFinding],
        *,
        target_vulnerability_id: str | None = None,
    ) -> AttackComparisonReport:
        """Analyze changes in findings between pre-repair and post-repair states."""
        pre_targets = {f.target_id: f.finding_id for f in pre_findings}
        post_targets = {f.target_id: f.finding_id for f in post_findings}

        resolved: list[str] = []
        persisting: list[str] = []
        new_vulns: list[str] = []

        for target_id, fid in pre_targets.items():
            if target_id in post_targets:
                persisting.append(fid)
            else:
                resolved.append(fid)

        for target_id, fid in post_targets.items():
            if target_id not in pre_targets:
                new_vulns.append(fid)

        net_improvement = len(resolved) - len(new_vulns)

        return AttackComparisonReport(
            pre_repair_finding_count=len(pre_findings),
            post_repair_finding_count=len(post_findings),
            resolved_findings=resolved,
            persisting_findings=persisting,
            new_findings=new_vulns,
            net_improvement=net_improvement,
        )
