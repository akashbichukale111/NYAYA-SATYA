"""Stability analysis for NYAYA-SATYA Legal Perturbation Lab.

Aggregates outcomes from perturbation experiments to assess structural reasoning resilience.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from nyaya_perturbation.perturbation_scenario import (
    PerturbationOutcome,
    PerturbationResultType,
)


@dataclass
class StabilityReport:
    """Consolidated summary of case reasoning stability under perturbation stress."""

    case_id: str
    total_experiments: int
    passed_count: int
    failed_count: int
    stability_score: float  # [0.0, 1.0]
    expected_changes_confirmed: int
    unexpected_changes_detected: int
    expected_changes_missing: int
    is_resilient: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StabilityAnalyzer:
    """Analyzes perturbation results to gauge structural case stability."""

    def analyze_stability(
        self,
        case_id: str,
        outcomes: list[PerturbationOutcome],
    ) -> StabilityReport:
        """Compute structural stability report from a set of perturbation outcomes."""
        if not outcomes:
            return StabilityReport(
                case_id=case_id,
                total_experiments=0,
                passed_count=0,
                failed_count=0,
                stability_score=1.0,
                expected_changes_confirmed=0,
                unexpected_changes_detected=0,
                expected_changes_missing=0,
                is_resilient=True,
                summary="No perturbation experiments run yet.",
            )

        passed = sum(1 for o in outcomes if o.is_safe)
        failed = len(outcomes) - passed
        score = round(passed / len(outcomes), 4)

        confirmed = sum(
            1 for o in outcomes
            if o.result_type in (PerturbationResultType.EXPECTED_CHANGE, PerturbationResultType.EXPECTED_NO_CHANGE)
        )
        unexpected = sum(
            1 for o in outcomes
            if o.result_type == PerturbationResultType.UNEXPECTED_CHANGE
        )
        missing = sum(
            1 for o in outcomes
            if o.result_type == PerturbationResultType.EXPECTED_CHANGE_MISSING
        )

        resilient = failed == 0 and score == 1.0
        summary = (
            f"Perturbation stability: {passed}/{len(outcomes)} experiments passed "
            f"({score * 100:.1f}%). {unexpected} unexpected propagations, {missing} missing changes."
        )

        return StabilityReport(
            case_id=case_id,
            total_experiments=len(outcomes),
            passed_count=passed,
            failed_count=failed,
            stability_score=score,
            expected_changes_confirmed=confirmed,
            unexpected_changes_detected=unexpected,
            expected_changes_missing=missing,
            is_resilient=resilient,
            summary=summary,
        )
