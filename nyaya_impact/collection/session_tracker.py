"""Session and phase latency tracker for NYAYA-SATYA Proven Impact subsystem.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_impact.collection.event_collector import EventCollector
from nyaya_impact.contracts.impact_event import ImpactEvent, ImpactEventType


@dataclass
class ActiveSession:
    session_id: str
    case_id: str
    phase: str
    start_time: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionTracker:
    """Tracks phase execution durations and emits telemetry events to an EventCollector."""

    def __init__(self, collector: EventCollector | None = None) -> None:
        self._collector = collector or EventCollector()
        self._active_sessions: dict[str, ActiveSession] = {}

    @property
    def active_sessions_count(self) -> int:
        return len(self._active_sessions)

    def start_phase(
        self,
        case_id: str,
        phase: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Start a tracked analytical phase."""
        session_id = f"SESS_{uuid.uuid4().hex[:8]}"
        session = ActiveSession(
            session_id=session_id,
            case_id=case_id,
            phase=phase,
            start_time=time.perf_counter(),
            metadata=metadata or {},
        )
        self._active_sessions[session_id] = session
        return session_id

    def end_phase(
        self,
        session_id: str,
        event_type: ImpactEventType,
        *,
        item_count: int = 1,
        additional_metadata: dict[str, Any] | None = None,
        provenance_hash: str | None = None,
    ) -> ImpactEvent:
        """End a tracked phase and emit an ImpactEvent."""
        if session_id not in self._active_sessions:
            raise KeyError(f"Active session {session_id} not found")

        sess = self._active_sessions.pop(session_id)
        duration_ms = (time.perf_counter() - sess.start_time) * 1000.0

        meta = dict(sess.metadata)
        if additional_metadata:
            meta.update(additional_metadata)

        event = ImpactEvent(
            event_id=f"EVT_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            case_id=sess.case_id,
            phase=sess.phase,
            duration_ms=duration_ms,
            item_count=item_count,
            metadata=meta,
            provenance_hash=provenance_hash,
        )
        self._collector.record_event(event)
        return event

    def reset_for_test(self) -> None:
        self._active_sessions.clear()
        self._collector.reset_for_test()
