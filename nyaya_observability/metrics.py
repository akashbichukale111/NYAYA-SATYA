"""Metrics collection and monitoring for NYAYA-SATYA Observability Subsystem.

Tracks request latencies, error distributions, upload failures, parser errors,
adversarial analysis durations, and security violations.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricSummary:
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0

    @property
    def avg_time_ms(self) -> float:
        return self.total_time_ms / self.count if self.count > 0 else 0.0

    def record(self, duration_ms: float) -> None:
        self.count += 1
        self.total_time_ms += duration_ms
        if duration_ms < self.min_time_ms:
            self.min_time_ms = duration_ms
        if duration_ms > self.max_time_ms:
            self.max_time_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2) if self.count > 0 else 0.0,
            "max_time_ms": round(self.max_time_ms, 2),
        }


class ObservabilityMetricsRegistry:
    """Thread-safe registry for operational and security metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._request_counts: dict[str, int] = defaultdict(int)
        self._error_counts: dict[int, int] = defaultdict(int)
        self._durations: dict[str, MetricSummary] = defaultdict(MetricSummary)
        self._upload_failures: dict[str, int] = defaultdict(int)
        self._parser_failures: dict[str, int] = defaultdict(int)
        self._security_events: dict[str, int] = defaultdict(int)

    def record_request(self, endpoint: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._request_counts[endpoint] += 1
            if status_code >= 400:
                self._error_counts[status_code] += 1
            self._durations[endpoint].record(duration_ms)

    def record_upload_failure(self, reason: str) -> None:
        with self._lock:
            self._upload_failures[reason] += 1
            self._security_events["upload_failure"] += 1

    def record_parser_failure(self, parser_name: str) -> None:
        with self._lock:
            self._parser_failures[parser_name] += 1

    def record_security_event(self, event_type: str) -> None:
        with self._lock:
            self._security_events[event_type] += 1

    def record_analysis_duration(self, analysis_type: str, duration_ms: float) -> None:
        with self._lock:
            self._durations[f"analysis:{analysis_type}"].record(duration_ms)

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            total_requests = sum(self._request_counts.values())
            total_errors = sum(self._error_counts.values())
            return {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_requests) if total_requests > 0 else 0.0,
                "requests_by_endpoint": dict(self._request_counts),
                "errors_by_status": dict(self._error_counts),
                "durations": {k: v.to_dict() for k, v in self._durations.items()},
                "upload_failures": dict(self._upload_failures),
                "parser_failures": dict(self._parser_failures),
                "security_events": dict(self._security_events),
            }

    def reset_for_test(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._error_counts.clear()
            self._durations.clear()
            self._upload_failures.clear()
            self._parser_failures.clear()
            self._security_events.clear()


# Global singleton instance
_GLOBAL_METRICS = ObservabilityMetricsRegistry()


def get_metrics_registry() -> ObservabilityMetricsRegistry:
    return _GLOBAL_METRICS


__all__ = [
    "MetricSummary",
    "ObservabilityMetricsRegistry",
    "get_metrics_registry",
]
