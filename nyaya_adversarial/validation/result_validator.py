"""Result Validator for NYAYA-SATYA Adversarial Subsystem.

Enforces the Strict Non-Adjudication Guarantee across all findings and reports.
PROHIBITS:
- Verdict prediction
- Win probability estimation
- Determinations of guilt, fraud, perjury, or liability
- Speculative outcome optimization
"""

from __future__ import annotations

import re
from typing import Any

from nyaya_adversarial.contracts.result import AdversarialFinding, AdversarialGauntletReport


class AdjudicationViolationError(ValueError):
    """Raised when an adversarial finding attempts to act as a judge or predict verdicts."""


class ResultValidator:
    """Validates that findings comply strictly with non-adjudication and structural safety."""

    PROHIBITED_TERMS = [
        re.compile(r"\bwin\s+probability\b", re.IGNORECASE),
        re.compile(r"\bchance\s+of\s+winning\b", re.IGNORECASE),
        re.compile(r"\bchance\s+of\s+losing\b", re.IGNORECASE),
        re.compile(r"\bverdict\s+prediction\b", re.IGNORECASE),
        re.compile(r"\bpredict(?:s|ed|ing)?\s+the\s+verdict\b", re.IGNORECASE),
        re.compile(r"\bguilty\s+as\s+charged\b", re.IGNORECASE),
        re.compile(r"\bguilty\s+of\s+fraud\b", re.IGNORECASE),
        re.compile(r"\bcommitted\s+perjury\b", re.IGNORECASE),
        re.compile(r"\bverdict\s*:\s*(?:guilty|liable|innocent)\b", re.IGNORECASE),
        re.compile(r"\b\d+%\s*(?:chance|probability)\s*of\s*(?:winning|losing)\b", re.IGNORECASE),
    ]

    def validate_finding(self, finding: AdversarialFinding) -> None:
        """Asserts that an individual finding is strictly structural and non-adjudicative."""
        text = f"{finding.explanation} {finding.status} {finding.structural_impact}"

        for pat in self.PROHIBITED_TERMS:
            match = pat.search(text)
            if match:
                raise AdjudicationViolationError(
                    f"NON-ADJUDICATION VIOLATION: Finding {finding.finding_id} contains prohibited adjudicative term: "
                    f"'{match.group(0)}'. NYAYA-SATYA never predicts verdicts or judges guilt."
                )

        if not finding.explanation or len(finding.explanation.strip()) < 10:
            raise ValueError(f"Finding {finding.finding_id} lacks an adequate explanation")

    def validate_report(self, report: AdversarialGauntletReport) -> None:
        """Validates all findings in an AdversarialGauntletReport."""
        for finding in report.findings:
            self.validate_finding(finding)
