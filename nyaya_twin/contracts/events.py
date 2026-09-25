"""Timeline event contracts for NYAYA-SATYA Case Digital Twin.

Models chronologically situated events.
Strictly preserves temporal precision (EXACT, DATE, MONTH, YEAR, RANGE, UNKNOWN).
Never invents or fabricates an exact timestamp from an approximate statement.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from tarka_vyuh.contracts.provenance import ProvenanceRef


class TimePrecision(str, Enum):
    EXACT = "EXACT"
    DATE = "DATE"
    MONTH = "MONTH"
    YEAR = "YEAR"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


class TemporalStatus(str, Enum):
    ORDERED = "ORDERED"
    APPROXIMATE = "APPROXIMATE"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class TimelineEvent:
    """A chronologically anchored factual event in the matter."""

    event_id: str
    case_id: str
    event_type: str
    title: str
    description: str = ""
    event_time: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    time_precision: TimePrecision = TimePrecision.UNKNOWN
    participants: list[str] = field(default_factory=list)
    location: str | None = None
    source_evidence_ids: list[str] = field(default_factory=list)
    related_claim_ids: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    temporal_status: TemporalStatus = TemporalStatus.ORDERED
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.event_id or not self.event_id.strip():
            raise ValueError("event_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.title or not self.title.strip():
            raise ValueError("title cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.event_id):
            raise ValueError(f"Invalid event_id format: {self.event_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")

        # Guard against precision fabrication
        if self.time_precision is TimePrecision.UNKNOWN:
            if self.event_time or self.start_time or self.end_time:
                # If times are supplied, precision cannot remain UNKNOWN
                self.time_precision = TimePrecision.APPROXIMATE if hasattr(TimePrecision, "APPROXIMATE") else TimePrecision.DATE
        elif self.time_precision is TimePrecision.EXACT:
            if not self.event_time:
                raise ValueError("EXACT precision requires an explicit event_time")
        elif self.time_precision in (TimePrecision.MONTH, TimePrecision.YEAR):
            # Prohibit timestamp fabrication down to seconds/minutes if declared month/year
            if self.event_time and ":" in self.event_time:
                raise ValueError(
                    f"Fabrication error: event declared precision {self.time_precision.value} "
                    f"cannot have exact time-of-day {self.event_time!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["time_precision"] = self.time_precision.value
        data["temporal_status"] = self.temporal_status.value
        data["confidence"] = self.confidence.value
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        d = dict(data)
        if isinstance(d.get("time_precision"), str):
            d["time_precision"] = TimePrecision(d["time_precision"])
        if isinstance(d.get("temporal_status"), str):
            d["temporal_status"] = TemporalStatus(d["temporal_status"])
        if isinstance(d.get("confidence"), str):
            d["confidence"] = ConfidenceLevel(d["confidence"])
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        if "provenance_refs" in d:
            d["provenance_refs"] = [
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            ]
        return cls(**d)
