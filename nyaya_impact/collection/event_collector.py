"""Append-only event collector for NYAYA-SATYA Proven Impact subsystem.

Stores and queries privacy-minimized structural workflow events.
"""

from __future__ import annotations

import threading
from typing import Any

from nyaya_impact.contracts.impact_event import ImpactEvent, ImpactEventType


class EventCollector:
    """Thread-safe append-only collector for structural workflow events."""

    def __init__(self) -> None:
        self._events: list[ImpactEvent] = []
        self._lock = threading.Lock()

    def record_event(self, event: ImpactEvent) -> None:
        """Record an immutable impact event."""
        with self._lock:
            self._events.append(event)

    def get_events_for_case(self, case_id: str) -> list[ImpactEvent]:
        """Query events for a specific case."""
        with self._lock:
            return [e for e in self._events if e.case_id == case_id]

    def get_events_by_type(self, event_type: ImpactEventType) -> list[ImpactEvent]:
        """Query events by type."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def count_by_type(self, case_id: str, event_type: ImpactEventType) -> int:
        """Count occurrences of an event type for a case."""
        with self._lock:
            return sum(1 for e in self._events if e.case_id == case_id and e.event_type == event_type)

    def total_duration_ms(self, case_id: str, phase: str | None = None) -> float:
        """Calculate total recorded duration for a case and optional phase."""
        with self._lock:
            matching = [
                e.duration_ms for e in self._events
                if e.case_id == case_id and (phase is None or e.phase == phase)
            ]
            return sum(matching)

    def all_events(self) -> list[ImpactEvent]:
        """Retrieve copy of all recorded events."""
        with self._lock:
            return list(self._events)

    def reset_for_test(self) -> None:
        with self._lock:
            self._events.clear()


ImpactEventCollector = EventCollector

