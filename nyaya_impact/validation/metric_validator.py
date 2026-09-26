"""Metric validation for NYAYA-SATYA Proven Impact subsystem.

Validates that metrics adhere to epistemic classifications, numerical bounds,
and strictly omit forbidden predictive claims.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricCategory, MetricClassification

FORBIDDEN_PREDICTIVE_PATTERNS = [
    r"win\s*rate",
    r"win\s*probability",
    r"case\s*strength",
    r"guilt\s*probability",
    r"verdict\s*predictor",
    r"guaranteed\s*win",
    r"liability\s*score",
    r"100%\s*accuracy",
]


@dataclass
class MetricValidationResult:
    """Validation outcome for an ImpactMetric."""

    is_valid: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MetricValidator:
    """Validates impact metrics against epistemic and integrity constraints."""

    def validate_metric(self, metric: ImpactMetric) -> MetricValidationResult:
        """Validate a single impact metric."""
        violations: list[str] = []
        warnings: list[str] = []

        # 1. Epistemic classification check
        if not isinstance(metric.classification, MetricClassification):
            violations.append(f"Invalid classification: {metric.classification}")

        # 2. Category check
        if not isinstance(metric.category, MetricCategory):
            violations.append(f"Invalid category: {metric.category}")

        # 3. Numeric bounds check
        if isinstance(metric.value, (int, float)):
            if "ratio" in metric.metric_id.lower() or "coverage" in metric.metric_id.lower() or metric.unit == "ratio":
                if metric.value < 0.0 or metric.value > 1.0:
                    violations.append(f"Ratio metric {metric.metric_id} value {metric.value} must be between 0.0 and 1.0")
            elif "latency" in metric.metric_id.lower() or "time" in metric.metric_id.lower() or "seconds" in metric.unit:
                if metric.value < 0.0:
                    violations.append(f"Time metric {metric.metric_id} cannot be negative: {metric.value}")
            elif "count" in metric.metric_id.lower():
                if metric.value < 0:
                    violations.append(f"Count metric {metric.metric_id} cannot be negative: {metric.value}")

        # 4. Check for forbidden predictive or marketing phrasing
        combined_text = f"{metric.metric_id} {metric.name} {metric.description} {metric.notes}".lower()
        for pattern in FORBIDDEN_PREDICTIVE_PATTERNS:
            if re.search(pattern, combined_text):
                violations.append(
                    f"Forbidden predictive/marketing claim matching '{pattern}' found in metric {metric.metric_id}"
                )

        # 5. Provenance check
        if not metric.source_provenance_hash:
            warnings.append(f"Metric {metric.metric_id} lacks source_provenance_hash")

        return MetricValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    def validate_metrics(self, metrics: list[ImpactMetric]) -> MetricValidationResult:
        """Validate a list of metrics and aggregate findings."""
        all_violations: list[str] = []
        all_warnings: list[str] = []

        for m in metrics:
            res = self.validate_metric(m)
            all_violations.extend(res.violations)
            all_warnings.extend(res.warnings)

        return MetricValidationResult(
            is_valid=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings,
        )
