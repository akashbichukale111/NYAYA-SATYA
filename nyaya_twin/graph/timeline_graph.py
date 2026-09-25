"""Timeline Graph for NYAYA-SATYA Case Digital Twin.

Models chronological ordering of events, preserves time precision,
and detects temporal conflicts deterministically.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from nyaya_twin.contracts.events import TemporalStatus, TimelineEvent, TimePrecision


class TimelineGraph:
    """Graph structure managing chronological timeline and temporal conflict detection."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self._events: dict[str, TimelineEvent] = {}

    def add_event(self, event: TimelineEvent) -> None:
        if event.case_id != self.case_id:
            raise ValueError(
                f"Cross-case contamination: event {event.event_id} belongs to {event.case_id}, expected {self.case_id}"
            )
        self._events[event.event_id] = event

    def get_event(self, event_id: str) -> TimelineEvent | None:
        return self._events.get(event_id)

    def get_chronological_stream(self) -> list[TimelineEvent]:
        """Returns events sorted chronologically by primary time representation.

        Events with unknown timestamps are placed at the end in deterministic ID order.
        """
        known = []
        unknown = []
        for ev in self._events.values():
            key = ev.event_time or ev.start_time or ""
            if key and ev.time_precision is not TimePrecision.UNKNOWN:
                known.append((key, ev))
            else:
                unknown.append(ev)

        # Sort known by date string, then ID
        known_sorted = [ev for _, ev in sorted(known, key=lambda x: (x[0], x[1].event_id))]
        unknown_sorted = sorted(unknown, key=lambda x: x.event_id)
        return known_sorted + unknown_sorted

    def get_events_for_participant(self, participant: str) -> list[TimelineEvent]:
        """Returns events in which a participant took part."""
        norm = participant.strip().lower()
        matched = []
        for ev in self.get_chronological_stream():
            if any(p.strip().lower() == norm for p in ev.participants):
                matched.append(ev)
        return matched

    def detect_temporal_conflicts(self) -> list[dict[str, Any]]:
        """Identifies deterministic temporal inconsistencies between events sharing subjects/titles.

        Example:
        - Event A: Agreement execution asserted on 2024-03-10
        - Event B: Agreement execution asserted on 2024-04-15
        Emits TEMPORAL_CONFLICT without arbitrarily picking one as truth.
        """
        conflicts: list[dict[str, Any]] = []
        event_list = list(self._events.values())

        for i in range(len(event_list)):
            for j in range(i + 1, len(event_list)):
                ev1 = event_list[i]
                ev2 = event_list[j]

                # Check if events refer to the same occurrence/action
                t1 = ev1.title.strip().lower()
                t2 = ev2.title.strip().lower()
                tokens1 = set(re.findall(r"\w+", t1))
                tokens2 = set(re.findall(r"\w+", t2))

                # If titles share significant tokens (e.g. "agreement execution" vs "agreement signed")
                overlap = tokens1.intersection(tokens2)
                # Ignore trivial stop words
                significant_overlap = {tok for tok in overlap if len(tok) > 3}

                if len(significant_overlap) >= 2 or t1 == t2:
                    date1 = ev1.event_time or ev1.start_time
                    date2 = ev2.event_time or ev2.start_time

                    if date1 and date2 and date1 != date2:
                        conflicts.append({
                            "conflict_type": "TEMPORAL_CONFLICT",
                            "case_id": self.case_id,
                            "event_a_id": ev1.event_id,
                            "event_b_id": ev2.event_id,
                            "title_a": ev1.title,
                            "title_b": ev2.title,
                            "date_a": date1,
                            "date_b": date2,
                            "precision_a": ev1.time_precision.value,
                            "precision_b": ev2.time_precision.value,
                            "source_evidence_a": list(ev1.source_evidence_ids),
                            "source_evidence_b": list(ev2.source_evidence_ids),
                            "status": "UNRESOLVED",
                        })

        return conflicts
