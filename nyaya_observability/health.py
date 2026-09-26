"""Health and liveness probes for NYAYA-SATYA Observability Subsystem.

Answers: Is the process alive and responsive?
Does not expose secrets, sensitive configuration, or internal memory states.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from typing import Any

# Process start time for uptime calculation
_PROCESS_START_TIME = time.time()


def get_uptime_seconds() -> float:
    return time.time() - _PROCESS_START_TIME


def check_liveness() -> dict[str, Any]:
    """Lightweight liveness check for container orchestrators and load balancers."""
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": round(get_uptime_seconds(), 2),
        "python_version": sys.version.split()[0],
        "pid": os.getpid(),
    }


__all__ = [
    "check_liveness",
    "get_uptime_seconds",
]
