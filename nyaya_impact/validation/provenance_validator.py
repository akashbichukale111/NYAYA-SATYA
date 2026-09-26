"""Provenance validation for NYAYA-SATYA Proven Impact subsystem.

Verifies cryptographic signatures, hashes, and chain-of-custody for impact data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from nyaya_impact.contracts.impact_measurement import ImpactMeasurement
from nyaya_impact.contracts.impact_report import ProvenImpactReport


@dataclass
class ProvenanceValidationResult:
    """Outcome of verifying cryptographic provenance."""

    is_valid: bool
    verified_hash: str
    details: list[str] = field(default_factory=list)


class ProvenanceValidator:
    """Verifies cryptographic provenance across measurements and reports."""

    def verify_measurement(self, measurement: ImpactMeasurement) -> ProvenanceValidationResult:
        """Verify the internal cryptographic fingerprint of an ImpactMeasurement."""
        expected = measurement.fingerprint
        payload = {
            "measurement_id": measurement.measurement_id,
            "target": measurement.case_or_dataset_id,
            "metric_id": measurement.metric.metric_id,
            "val": measurement.metric.value,
            "classification": measurement.metric.classification.value,
            "experiment": measurement.experiment_id,
            "prov": measurement.provenance_hash,
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        actual = hashlib.sha256(dumped.encode("utf-8")).hexdigest()

        match = actual == expected
        details = [f"Actual: {actual}", f"Expected: {expected}"]
        if not match:
            details.append("Fingerprint mismatch detected! Measurement may have been tampered with.")

        return ProvenanceValidationResult(
            is_valid=match,
            verified_hash=actual,
            details=details,
        )

    def verify_report(self, report: ProvenImpactReport) -> ProvenanceValidationResult:
        """Verify the internal cryptographic fingerprint of a ProvenImpactReport."""
        expected = report.fingerprint
        payload = {
            "report_id": report.report_id,
            "target": report.case_or_dataset_id,
            "scope": report.sec01_scope,
            "dataset": report.sec02_dataset,
            "results": report.sec07_results,
            "findings": sorted(report.sec08_structural_findings),
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        actual = hashlib.sha256(dumped.encode("utf-8")).hexdigest()

        match = actual == expected
        details = [f"Actual: {actual}", f"Expected: {expected}"]
        if not match:
            details.append("Fingerprint mismatch detected! Report content may have been modified.")

        return ProvenanceValidationResult(
            is_valid=match,
            verified_hash=actual,
            details=details,
        )
