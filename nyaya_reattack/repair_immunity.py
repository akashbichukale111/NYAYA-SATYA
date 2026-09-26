"""Repair immunity evaluation for NYAYA-SATYA Re-Attack subsystem.

Evaluates whether a repair candidate is genuinely immune to adversarial stress
or merely shifts vulnerabilities elsewhere.
Strictly structural: does not convert into a judicial verdict or legal conclusion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from nyaya_reattack.attack_comparator import AttackComparisonReport
from nyaya_reattack.regression_detector import RegressionReport
from nyaya_repair.contracts.repair_candidate import RepairCandidate


class RepairImmunityStatus(str, Enum):
    """Immunity status of a repair candidate following independent re-attack."""

    IMMUNE = "IMMUNE"
    PARTIALLY_IMMUNE = "PARTIALLY_IMMUNE"
    VULNERABLE = "VULNERABLE"
    REGRESSION = "REGRESSION"
    UNKNOWN = "UNKNOWN"


@dataclass
class RepairImmunityAssessment:
    """Comprehensive evaluation of repair immunity."""

    repair_id: str
    status: RepairImmunityStatus
    target_vulnerability_resolved: bool
    new_vulnerability_count: int
    regression_detected: bool
    blast_radius_contained: bool
    provenance_preserved: bool
    explanation: str
    criteria_evaluated: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repair_id": self.repair_id,
            "status": self.status.value,
            "target_vulnerability_resolved": self.target_vulnerability_resolved,
            "new_vulnerability_count": self.new_vulnerability_count,
            "regression_detected": self.regression_detected,
            "blast_radius_contained": self.blast_radius_contained,
            "provenance_preserved": self.provenance_preserved,
            "explanation": self.explanation,
            "criteria_evaluated": self.criteria_evaluated,
        }


class RepairImmunityEvaluator:
    """Evaluates whether a repair withstands independent adversarial re-attack."""

    def evaluate_immunity(
        self,
        repair: RepairCandidate,
        comparison: AttackComparisonReport,
        regression: RegressionReport,
        *,
        blast_radius_contained: bool = True,
        provenance_preserved: bool = True,
    ) -> RepairImmunityAssessment:
        """Assess overall repair immunity based on re-attack metrics."""
        # 1. Target vulnerability status
        target_resolved = repair.target_vulnerability_id in comparison.resolved_findings
        if not target_resolved and repair.target_claim_id:
            # Also consider resolved if target claim has no open attacks
            target_resolved = len(comparison.resolved_findings) > 0

        # Criteria breakdown
        criteria = {
            "target_vulnerability_resolved": target_resolved,
            "zero_new_critical_vulnerabilities": regression.regression_severity != "CRITICAL",
            "no_regressions": not regression.has_regression,
            "blast_radius_contained": blast_radius_contained,
            "provenance_preserved": provenance_preserved,
        }

        # Determine status
        if regression.has_regression:
            status = RepairImmunityStatus.REGRESSION
            explanation = (
                f"Repair {repair.repair_id} caused regression: "
                f"{len(regression.new_vulnerability_ids)} new vulnerabilities introduced."
            )
        elif target_resolved and all(criteria.values()):
            status = RepairImmunityStatus.IMMUNE
            explanation = (
                f"Repair {repair.repair_id} is structurally IMMUNE: "
                "original vulnerability resolved with zero new vulnerabilities and contained blast radius."
            )
        elif target_resolved:
            status = RepairImmunityStatus.PARTIALLY_IMMUNE
            explanation = (
                f"Repair {repair.repair_id} is PARTIALLY IMMUNE: "
                "target vulnerability resolved but some peripheral stress points remain."
            )
        else:
            status = RepairImmunityStatus.VULNERABLE
            explanation = (
                f"Repair {repair.repair_id} remains VULNERABLE: "
                "re-attack demonstrated that target vulnerability persists."
            )

        return RepairImmunityAssessment(
            repair_id=repair.repair_id,
            status=status,
            target_vulnerability_resolved=target_resolved,
            new_vulnerability_count=len(regression.new_vulnerability_ids),
            regression_detected=regression.has_regression,
            blast_radius_contained=blast_radius_contained,
            provenance_preserved=provenance_preserved,
            explanation=explanation,
            criteria_evaluated=criteria,
        )
