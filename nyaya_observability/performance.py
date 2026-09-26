"""Performance measurement and benchmarking utilities for NYAYA-SATYA.

Provides high-resolution timers and execution profilers for tracking evidence ingestion,
graph traversal, causal simulation, and dossier generation latencies.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from nyaya_observability.metrics import get_metrics_registry


@contextmanager
def measure_execution_time(operation_name: str) -> Iterator[dict[str, Any]]:
    """Context manager measuring execution duration in milliseconds."""
    result: dict[str, Any] = {"operation": operation_name, "duration_ms": 0.0}
    start = time.perf_counter()
    try:
        yield result
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        result["duration_ms"] = round(elapsed_ms, 2)
        get_metrics_registry().record_analysis_duration(operation_name, elapsed_ms)


__all__ = [
    "measure_execution_time",
]
