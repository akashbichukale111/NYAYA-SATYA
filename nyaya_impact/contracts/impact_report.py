"""Impact report contract for NYAYA-SATYA Proven Impact subsystem.

Defines the 14-section auditable impact report.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_impact.contracts.impact_metric import ImpactMetric


@dataclass
class ProvenImpactReport:
    """Canonical 14-section auditable Proven Impact Report."""

    report_id: str
    case_or_dataset_id: str
    sec01_scope: dict[str, Any] = field(default_factory=dict)
    sec02_dataset: dict[str, Any] = field(default_factory=dict)
    sec03_methodology: str = ""
    sec04_baseline: dict[str, Any] = field(default_factory=dict)
    sec05_nyaya_workflow: dict[str, Any] = field(default_factory=dict)
    sec06_metrics: list[ImpactMetric] = field(default_factory=list)
    sec07_results: dict[str, Any] = field(default_factory=dict)
    sec08_structural_findings: list[str] = field(default_factory=list)
    sec09_limitations: list[str] = field(default_factory=list)
    sec10_reproducibility: dict[str, Any] = field(default_factory=dict)
    sec11_deployment_evidence: dict[str, Any] = field(default_factory=dict)
    sec12_human_review: dict[str, Any] = field(default_factory=dict)
    sec13_security: dict[str, Any] = field(default_factory=dict)
    sec14_open_issues: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of report content."""
        payload = {
            "report_id": self.report_id,
            "target": self.case_or_dataset_id,
            "scope": self.sec01_scope,
            "dataset": self.sec02_dataset,
            "results": self.sec07_results,
            "findings": sorted(self.sec08_structural_findings),
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "case_or_dataset_id": self.case_or_dataset_id,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat(),
            "sec01_scope": self.sec01_scope,
            "sec02_dataset": self.sec02_dataset,
            "sec03_methodology": self.sec03_methodology,
            "sec04_baseline": self.sec04_baseline,
            "sec05_nyaya_workflow": self.sec05_nyaya_workflow,
            "sec06_metrics": [m.to_dict() for m in self.sec06_metrics],
            "sec07_results": self.sec07_results,
            "sec08_structural_findings": list(self.sec08_structural_findings),
            "sec09_limitations": list(self.sec09_limitations),
            "sec10_reproducibility": self.sec10_reproducibility,
            "sec11_deployment_evidence": self.sec11_deployment_evidence,
            "sec12_human_review": self.sec12_human_review,
            "sec13_security": self.sec13_security,
            "sec14_open_issues": list(self.sec14_open_issues),
        }
