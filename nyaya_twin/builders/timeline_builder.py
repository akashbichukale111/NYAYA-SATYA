"""Timeline Builder for NYAYA-SATYA Case Digital Twin.

Constructs timeline events with explicit time precision.
Prevents timestamp fabrication.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from nyaya_twin.contracts.confidence import ConfidenceLevel
from nyaya_twin.contracts.events import TemporalStatus, TimelineEvent, TimePrecision
from tarka_vyuh.contracts.provenance import ProvenanceRef


class TimelineBuilder:
    """Builder for constructing timeline events."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self._events: dict[str, TimelineEvent] = {}

    def add_event(
        self,
        *,
        title: str,
        event_id: str | None = None,
        event_type: str = "FACTUAL_EVENT",
        description: str = "",
        event_time: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        time_precision: TimePrecision = TimePrecision.UNKNOWN,
        participants: list[str] | None = None,
        location: str | None = None,
        source_evidence_ids: list[str] | None = None,
        related_claim_ids: list[str] | None = None,
        provenance_refs: list[ProvenanceRef] | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
        temporal_status: TemporalStatus = TemporalStatus.ORDERED,
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEvent:
        if event_id is None:
            clean_title = re.sub(r"[^a-zA-Z0-9]+", "_", title.strip()).strip("_").lower()
            event_id = f"evt_{clean_title}_{uuid.uuid4().hex[:6]}"

        event = TimelineEvent(
            event_id=event_id,
            case_id=self.case_id,
            event_type=event_type,
            title=title.strip(),
            description=description.strip(),
            event_time=event_time,
            start_time=start_time,
            end_time=end_time,
            time_precision=time_precision,
            participants=list(participants or []),
            location=location,
            source_evidence_ids=list(source_evidence_ids or []),
            related_claim_ids=list(related_claim_ids or []),
            provenance_refs=list(provenance_refs or []),
            confidence=confidence,
            temporal_status=temporal_status,
            metadata=dict(metadata or {}),
        )
        self._events[event.event_id] = event
        return event

    def get_events(self) -> dict[str, TimelineEvent]:
        return dict(self._events)
