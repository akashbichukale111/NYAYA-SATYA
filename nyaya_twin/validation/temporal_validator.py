"""Temporal Integrity Validator for NYAYA-SATYA Case Digital Twin.

Validates that declared event intervals are well-formed and discovers temporal conflicts.
Never fabricates exact timestamps.
"""

from __future__ import annotations

from typing import Any

from nyaya_twin.contracts.events import TimelineEvent, TimePrecision


class TemporalValidationError(ValueError):
    """Raised when temporal event intervals are malformed."""


def validate_temporal_integrity(events: list[TimelineEvent]) -> list[str]:
    """Validates that event time representations conform to precision rules.

    Returns a list of validation error descriptions.
    """
    errors: list[str] = []

    for ev in events:
        # Check start_time and end_time ordering if both present
        if ev.start_time and ev.end_time:
            if ev.start_time > ev.end_time:
                errors.append(
                    f"Temporal inversion in event {ev.event_id}: start_time {ev.start_time!r} is after end_time {ev.end_time!r}"
                )

        # Unknown precision cannot have timestamps
        if ev.time_precision is TimePrecision.UNKNOWN:
            if ev.event_time or ev.start_time or ev.end_time:
                errors.append(
                    f"Event {ev.event_id} has declared UNKNOWN precision but provides explicit timestamps"
                )

        # Month precision must follow YYYY-MM
        if ev.time_precision is TimePrecision.MONTH:
            for t in (ev.event_time, ev.start_time, ev.end_time):
                if t and len(t.strip()) > 7 and "-" in t and ":" in t:
                    errors.append(
                        f"Event {ev.event_id} declares MONTH precision but specifies exact time {t!r}"
                    )

        # Year precision must follow YYYY
        if ev.time_precision is TimePrecision.YEAR:
            for t in (ev.event_time, ev.start_time, ev.end_time):
                if t and len(t.strip()) > 4 and "-" in t:
                    errors.append(
                        f"Event {ev.event_id} declares YEAR precision but specifies more granular date {t!r}"
                    )

    return errors
