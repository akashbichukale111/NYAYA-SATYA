"""Real Deployment Impact Tracker for NYAYA-SATYA.

Connects production-safe telemetry to Phase 7 Proven Impact subsystem.
Strictly adheres to the NON-FABRICATION mandate:
If no real users/cases exist in production:
STATUS = NO_REAL_DEPLOYMENT_DATA_YET

Never fabricates users, hours saved, or judicial outcomes.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from nyaya_impact.contracts.impact_metric import EpistemicStatus


class RealDeploymentTracker:
    """Tracks authenticated real deployment usage without simulating or fabricating data."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._real_sessions: dict[str, dict[str, Any]] = {}
        self._real_cases: set[str] = set()
        self._real_events_count: int = 0

    def record_real_case_activity(self, case_id: str, principal_id: str, action: str) -> None:
        """Records an actual user interaction in production."""
        with self._lock:
            # Only record if not synthetic or test
            if "synth" in case_id.lower() or "test" in case_id.lower() or "bm_" in case_id.lower():
                return
            self._real_cases.add(case_id)
            self._real_events_count += 1
            self._real_sessions[principal_id] = {
                "last_active": datetime.now(UTC).isoformat(),
                "case_id": case_id,
                "action": action,
            }

    def get_deployment_status(self) -> dict[str, Any]:
        """Returns the honest real deployment impact status."""
        with self._lock:
            if not self._real_cases or not self._real_sessions:
                return {
                    "status": "NO_REAL_DEPLOYMENT_DATA_YET",
                    "epistemic_classification": EpistemicStatus.REAL_DEPLOYMENT.value,
                    "real_users_count": 0,
                    "real_cases_count": 0,
                    "real_events_count": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "statement": (
                        "Zero real deployment cases or users recorded yet. "
                        "All available benchmark evaluations are strictly classified as SYNTHETIC. "
                        "NYAYA-SATYA strictly prohibits fabricating deployment impact."
                    ),
                }

            return {
                "status": "ACTIVE_DEPLOYMENT",
                "epistemic_classification": EpistemicStatus.REAL_DEPLOYMENT.value,
                "real_users_count": len(self._real_sessions),
                "real_cases_count": len(self._real_cases),
                "real_events_count": self._real_events_count,
                "timestamp": datetime.now(UTC).isoformat(),
                "statement": "Real production usage observed under strict privacy minimization.",
            }

    def reset_for_test(self) -> None:
        with self._lock:
            self._real_sessions.clear()
            self._real_cases.clear()
            self._real_events_count = 0


_GLOBAL_REAL_DEPLOYMENT_TRACKER = RealDeploymentTracker()


def get_real_deployment_tracker() -> RealDeploymentTracker:
    return _GLOBAL_REAL_DEPLOYMENT_TRACKER


__all__ = [
    "RealDeploymentTracker",
    "get_real_deployment_tracker",
]
