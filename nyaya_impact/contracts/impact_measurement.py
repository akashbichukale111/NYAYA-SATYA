"""Impact measurement record contracts for NYAYA-SATYA Proven Impact subsystem.

Preserves append-only immutable measurement entries with cryptographic integrity.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_impact.contracts.impact_metric import ImpactMetric, MetricClassification


@dataclass(frozen=True)
class ImpactMeasurement:
    """An immutable, append-only measurement entry."""

    measurement_id: str
    case_or_dataset_id: str
    metric: ImpactMetric
    software_version: str = "7.0.0"
    git_commit_sha: str | None = None
    experiment_id: str | None = None
    provenance_hash: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of semantic measurement content."""
        payload = {
            "measurement_id": self.measurement_id,
            "target": self.case_or_dataset_id,
            "metric_id": self.metric.metric_id,
            "val": self.metric.value,
            "classification": self.metric.classification.value,
            "experiment": self.experiment_id,
            "prov": self.provenance_hash,
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "case_or_dataset_id": self.case_or_dataset_id,
            "metric": self.metric.to_dict(),
            "software_version": self.software_version,
            "git_commit_sha": self.git_commit_sha,
            "experiment_id": self.experiment_id,
            "provenance_hash": self.provenance_hash,
            "fingerprint": self.fingerprint,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImpactMeasurement:
        d = dict(data)
        d.pop("fingerprint", None)
        if "metric" in d:
            d["metric"] = ImpactMetric.from_dict(d["metric"])
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)
