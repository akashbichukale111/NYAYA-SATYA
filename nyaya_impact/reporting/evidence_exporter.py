"""Evidence exporter for NYAYA-SATYA Proven Impact subsystem.

Exports audit packages, reports, and measurements with cryptographic fingerprints.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from nyaya_impact.contracts.impact_measurement import ImpactMeasurement
from nyaya_impact.contracts.impact_report import ProvenImpactReport
from nyaya_impact.reporting.impact_report import ImpactReportCompiler


class EvidenceExporter:
    """Exports and signs impact reports and measurements for third-party audit."""

    def __init__(self, compiler: ImpactReportCompiler | None = None) -> None:
        self.compiler = compiler or ImpactReportCompiler()

    def export_json(self, report: ProvenImpactReport) -> str:
        """Export report as JSON envelope with integrity signature."""
        data = report.to_dict()
        canonical_bytes = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = {
            "nyaya_proven_impact_version": "2.0",
            "report_fingerprint": report.fingerprint,
            "sha256_checksum": hashlib.sha256(canonical_bytes).hexdigest(),
            "payload": data,
        }
        return json.dumps(envelope, indent=2, sort_keys=True)

    def export_markdown(self, report: ProvenImpactReport) -> str:
        """Export report as human-readable Markdown with verification footer."""
        md = self.compiler.generate_markdown(report)
        footer = [
            "---",
            f"**Audit Checksum**: `sha256:{report.fingerprint}`",
            "**Epistemic Rule**: Verified without outcome prediction. Human Legal Gate retains final decision authority.",
            "",
        ]
        return md + "\n" + "\n".join(footer)

    def verify_json_export(self, json_str: str) -> bool:
        """Verify the integrity of an exported JSON envelope."""
        try:
            envelope = json.loads(json_str)
            payload = envelope.get("payload")
            expected_checksum = envelope.get("sha256_checksum")
            if not payload or not expected_checksum:
                return False

            canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            actual_checksum = hashlib.sha256(canonical_bytes).hexdigest()
            return actual_checksum == expected_checksum
        except Exception:
            return False
