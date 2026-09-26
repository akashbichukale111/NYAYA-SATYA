"""Impact safety validator enforcing zero fake impact, privacy, and non-adjudication.

Mandates:
1. NO FAKE IMPACT: No fabricated users, fake time saved, or fake win rates.
2. PRIVACY MINIMIZATION: Zero PII (Aadhaar, PAN, phone, email, SSN).
3. NON-ADJUDICATION: Zero verdict predictions, guilt/liability findings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nyaya_impact.contracts.impact_event import ImpactEvent
from nyaya_impact.contracts.impact_metric import ImpactMetric
from nyaya_impact.contracts.impact_report import ProvenImpactReport

# Indian PII Patterns & Common PII
PII_PATTERNS = [
    (r"\b[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}\b", "Aadhaar number detected"),
    (r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "PAN card number detected"),
    (r"\b[6-9][0-9]{9}\b", "Indian 10-digit mobile number detected"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email address detected"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN detected"),
]

# Prohibited Non-Adjudication Patterns
PROHIBITED_ADJUDICATION_TERMS = [
    r"verdict\s*prediction",
    r"predict(?:ed|ing)?\s+the\s+verdict",
    r"judge\s*ruling",
    r"guilt\s*(?:score|assessment|rating)",
    r"innocen(?:ce|t)\s*(?:score|assessment|rating)",
    r"win\s*probability",
    r"liability\s*finding",
]

# Prohibited Fake Impact Marketing Buzzwords
PROHIBITED_MARKETING_TERMS = [
    r"100%\s*success",
    r"guaranteed\s*outcome",
    r"10x\s*lawyer\s*speedup",
    r"replaces\s*lawyers",
    r"autonomous\s*judge",
]


@dataclass
class ImpactSafetyResult:
    """Outcome of impact safety and compliance checks."""

    is_safe: bool
    violations: list[str] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, CRITICAL


class ImpactSafetyValidator:
    """Enforces non-adjudication, privacy minimization, and zero fake impact."""

    def check_text(self, text: str) -> list[str]:
        """Scan freeform text for PII or non-adjudication violations."""
        issues: list[str] = []

        # Check PII
        for pattern, label in PII_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"PRIVACY VIOLATION: {label}")

        # Check Adjudication
        for pattern in PROHIBITED_ADJUDICATION_TERMS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"NON-ADJUDICATION VIOLATION: Disallowed phrase matching '{pattern}'")

        # Check Fake Impact / Marketing
        for pattern in PROHIBITED_MARKETING_TERMS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"NO-FAKE-IMPACT VIOLATION: Disallowed phrase matching '{pattern}'")

        return issues

    def validate_event(self, event: ImpactEvent) -> ImpactSafetyResult:
        """Validate an impact event for safety and privacy compliance."""
        combined = f"{event.event_type.value} {json_dumps_safe(event.payload)}"
        violations = self.check_text(combined)

        risk = "LOW"
        if any("PRIVACY" in v for v in violations):
            risk = "CRITICAL"
        elif violations:
            risk = "MEDIUM"

        return ImpactSafetyResult(
            is_safe=len(violations) == 0,
            violations=violations,
            risk_level=risk,
        )

    def validate_metric(self, metric: ImpactMetric) -> ImpactSafetyResult:
        """Validate an impact metric for safety compliance."""
        combined = f"{metric.metric_id} {metric.name} {metric.description} {metric.notes} {json_dumps_safe(metric.metadata)}"
        violations = self.check_text(combined)

        risk = "LOW"
        if any("PRIVACY" in v for v in violations):
            risk = "CRITICAL"
        elif violations:
            risk = "MEDIUM"

        return ImpactSafetyResult(
            is_safe=len(violations) == 0,
            violations=violations,
            risk_level=risk,
        )

    def validate_report(self, report: ProvenImpactReport) -> ImpactSafetyResult:
        """Validate a full ProvenImpactReport against safety guidelines."""
        all_violations: list[str] = []

        # Check textual sections
        all_violations.extend(self.check_text(report.sec03_methodology))
        for item in report.sec08_structural_findings:
            all_violations.extend(self.check_text(item))
        for item in report.sec09_limitations:
            all_violations.extend(self.check_text(item))
        for item in report.sec14_open_issues:
            all_violations.extend(self.check_text(item))

        # Check metrics
        for m in report.sec06_metrics:
            m_res = self.validate_metric(m)
            all_violations.extend(m_res.violations)

        risk = "LOW"
        if any("PRIVACY" in v for v in all_violations):
            risk = "CRITICAL"
        elif all_violations:
            risk = "MEDIUM"

        return ImpactSafetyResult(
            is_safe=len(all_violations) == 0,
            violations=all_violations,
            risk_level=risk,
        )


def json_dumps_safe(val: Any) -> str:
    import json
    try:
        return json.dumps(val, default=str)
    except Exception:
        return str(val)
