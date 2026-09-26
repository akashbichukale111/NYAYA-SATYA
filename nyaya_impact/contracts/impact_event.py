"""Impact event telemetry models for NYAYA-SATYA Proven Impact subsystem.

Captures privacy-minimized structural workflow events across the analysis lifecycle.
Strictly excludes personal identifiable information (PII).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ImpactEventType(str, Enum):
    """Categorical types of verifiable analytical events."""

    EVIDENCE_INGESTED = "EVIDENCE_INGESTED"
    EVIDENCE_PARSED = "EVIDENCE_PARSED"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    MISSING_EVIDENCE_FOUND = "MISSING_EVIDENCE_FOUND"
    ADVERSARIAL_ATTACK_RUN = "ADVERSARIAL_ATTACK_RUN"
    REPAIR_PROPOSED = "REPAIR_PROPOSED"
    REPAIR_SIMULATED = "REPAIR_SIMULATED"
    REATTACK_COMPLETED = "REATTACK_COMPLETED"
    IMMUNITY_EVALUATED = "IMMUNITY_EVALUATED"
    PERTURBATION_RUN = "PERTURBATION_RUN"
    READINESS_CALCULATED = "READINESS_CALCULATED"
    DOSSIER_GENERATED = "DOSSIER_GENERATED"
    GATE_CHECKPOINT_REACHED = "GATE_CHECKPOINT_REACHED"
    GATE_DECISION_RECORDED = "GATE_DECISION_RECORDED"
    BENCHMARK_SCENARIO_RUN = "BENCHMARK_SCENARIO_RUN"


@dataclass(frozen=True)
class ImpactEvent:
    """An individual structural workflow telemetry event.

    Privacy-minimized: carries IDs, counts, hashes, and latencies. Never raw PII.
    """

    event_id: str
    event_type: ImpactEventType
    case_id: str
    phase: str
    duration_ms: float = 0.0
    item_count: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance_hash: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id cannot be blank")
        if not self.case_id:
            raise ValueError("case_id cannot be blank")

    @property
    def payload(self) -> dict[str, Any]:
        return self.metadata

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of semantic event attributes."""
        payload = {
            "event_id": self.event_id,
            "type": self.event_type.value,
            "case_id": self.case_id,
            "phase": self.phase,
            "count": self.item_count,
            "prov": self.provenance_hash,
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "case_id": self.case_id,
            "phase": self.phase,
            "duration_ms": round(self.duration_ms, 2),
            "item_count": self.item_count,
            "metadata": self.metadata,
            "provenance_hash": self.provenance_hash,
            "fingerprint": self.fingerprint,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImpactEvent:
        d = dict(data)
        d.pop("fingerprint", None)
        if isinstance(d.get("event_type"), str):
            d["event_type"] = ImpactEventType(d["event_type"])
        if isinstance(d.get("timestamp"), str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)
