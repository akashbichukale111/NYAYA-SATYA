"""Regression detection engine for NYAYA-SATYA Re-Attack subsystem.

Detects regressions introduced into case structure as side-effects of repair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_adversarial.contracts.result import AdversarialFinding
from nyaya_reattack.attack_comparator import AttackComparisonReport
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


@dataclass
class RegressionReport:
    """Detailed diagnosis of regressions detected post-repair."""

    has_regression: bool
    new_vulnerability_ids: list[str] = field(default_factory=list)
    regression_severity: str = "NONE"  # NONE, MINOR, CRITICAL
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_regression": self.has_regression,
            "new_vulnerability_ids": list(self.new_vulnerability_ids),
            "regression_severity": self.regression_severity,
            "reasons": list(self.reasons),
        }


class RegressionDetector:
    """Diagnoses whether a repair induced regressions."""

    def detect_regressions(
        self,
        comparison: AttackComparisonReport,
        post_findings: list[AdversarialFinding],
    ) -> RegressionReport:
        """Scan comparison and post-repair findings for regressions."""
        has_reg = len(comparison.new_findings) > 0
        reasons: list[str] = []
        severity = "NONE"

        if has_reg:
            critical_new = [
                f.finding_id for f in post_findings
                if f.finding_id in comparison.new_findings and f.severity.value in ("CRITICAL", "HIGH")
            ]
            if critical_new:
                severity = "CRITICAL"
                reasons.append(f"Critical or High severity new vulnerabilities introduced: {critical_new}")
            else:
                severity = "MINOR"
                reasons.append(f"{len(comparison.new_findings)} minor new vulnerabilities surfaced")

        return RegressionReport(
            has_regression=has_reg,
            new_vulnerability_ids=comparison.new_findings,
            regression_severity=severity,
            reasons=reasons,
        )
