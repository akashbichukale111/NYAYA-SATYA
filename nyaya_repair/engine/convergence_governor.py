"""Convergence Governor for NYAYA-SATYA Auto-Healer.

Prevents endless repair -> attack -> repair cycles.
Tracks repeated repair/attack fingerprints, vulnerability reduction,
and convergence states.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ConvergenceState(str, Enum):
    """Lifecycle state of repair-attack convergence."""

    NOT_STARTED = "NOT_STARTED"
    REPAIRING = "REPAIRING"
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    CONVERGED = "CONVERGED"
    STALLED = "STALLED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


@dataclass
class ConvergenceIterationRecord:
    """Record of a single iteration through repair and re-attack."""

    iteration_index: int
    repair_fingerprint: str
    attack_fingerprints: list[str]
    vulnerability_count_before: int
    vulnerability_count_after: int
    new_vulnerability_count: int
    state: ConvergenceState


class ConvergenceGovernor:
    """Monitors multi-pass repair-attack iterations to guarantee termination."""

    def __init__(
        self,
        *,
        max_iterations: int = 10,
        stalled_threshold: int = 2,
    ) -> None:
        self.max_iterations = max_iterations
        self.stalled_threshold = stalled_threshold
        self._seen_repair_fingerprints: set[str] = set()
        self._seen_attack_fingerprints: set[str] = set()
        self._history: list[ConvergenceIterationRecord] = []
        self._current_state: ConvergenceState = ConvergenceState.NOT_STARTED

    @property
    def current_state(self) -> ConvergenceState:
        return self._current_state

    @property
    def history(self) -> list[ConvergenceIterationRecord]:
        return list(self._history)

    def evaluate_iteration(
        self,
        *,
        repair_fingerprint: str,
        attack_fingerprints: list[str],
        vulnerability_count_before: int,
        vulnerability_count_after: int,
        new_vulnerability_count: int,
    ) -> tuple[ConvergenceState, str]:
        """Evaluate an iteration and determine the new convergence state."""
        iteration_index = len(self._history) + 1

        # Check 1: Repeated repair fingerprint -> immediate termination of path
        if repair_fingerprint in self._seen_repair_fingerprints:
            self._current_state = ConvergenceState.STALLED
            reason = (
                f"Repeated repair fingerprint detected ({repair_fingerprint[:12]}). "
                "Halting repair loop to prevent infinite cycle."
            )
            self._record(
                iteration_index, repair_fingerprint, attack_fingerprints,
                vulnerability_count_before, vulnerability_count_after,
                new_vulnerability_count, self._current_state,
            )
            return self._current_state, reason

        self._seen_repair_fingerprints.add(repair_fingerprint)
        for af in attack_fingerprints:
            self._seen_attack_fingerprints.add(af)

        # Check 2: Regression detected
        if new_vulnerability_count > 0:
            self._current_state = ConvergenceState.REGRESSION_DETECTED
            reason = (
                f"Regression detected: {new_vulnerability_count} new vulnerabilities introduced. "
                "Flagging for human review."
            )
            self._record(
                iteration_index, repair_fingerprint, attack_fingerprints,
                vulnerability_count_before, vulnerability_count_after,
                new_vulnerability_count, self._current_state,
            )
            return self._current_state, reason

        # Check 3: Converged (zero vulnerabilities remain)
        if vulnerability_count_after == 0:
            self._current_state = ConvergenceState.CONVERGED
            reason = "Case state converged: zero open structural vulnerabilities remaining."
            self._record(
                iteration_index, repair_fingerprint, attack_fingerprints,
                vulnerability_count_before, vulnerability_count_after,
                new_vulnerability_count, self._current_state,
            )
            return self._current_state, reason

        # Check 4: Improving
        if vulnerability_count_after < vulnerability_count_before:
            self._current_state = ConvergenceState.IMPROVING
            reason = (
                f"Vulnerabilities reduced from {vulnerability_count_before} to {vulnerability_count_after}."
            )
        # Check 5: Stalled (no improvement)
        elif vulnerability_count_after == vulnerability_count_before:
            stalled_runs = sum(
                1 for h in self._history[-self.stalled_threshold:]
                if h.vulnerability_count_after >= h.vulnerability_count_before
            )
            if stalled_runs >= self.stalled_threshold:
                self._current_state = ConvergenceState.HUMAN_REVIEW_REQUIRED
                reason = "Repair stalled across multiple passes. Human legal review required."
            else:
                self._current_state = ConvergenceState.STALLED
                reason = "No vulnerability reduction achieved in this pass."
        else:
            self._current_state = ConvergenceState.REGRESSION_DETECTED
            reason = f"Vulnerability count increased from {vulnerability_count_before} to {vulnerability_count_after}."

        # Check 6: Max iterations limit
        if iteration_index >= self.max_iterations:
            self._current_state = ConvergenceState.HUMAN_REVIEW_REQUIRED
            reason = f"Max iteration limit ({self.max_iterations}) reached. Escalate to Human Legal Gate."

        self._record(
            iteration_index, repair_fingerprint, attack_fingerprints,
            vulnerability_count_before, vulnerability_count_after,
            new_vulnerability_count, self._current_state,
        )
        return self._current_state, reason

    def _record(
        self,
        index: int,
        rep_fp: str,
        att_fps: list[str],
        before: int,
        after: int,
        new_vulns: int,
        state: ConvergenceState,
    ) -> None:
        self._history.append(
            ConvergenceIterationRecord(
                iteration_index=index,
                repair_fingerprint=rep_fp,
                attack_fingerprints=att_fps,
                vulnerability_count_before=before,
                vulnerability_count_after=after,
                new_vulnerability_count=new_vulns,
                state=state,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_state": self._current_state.value,
            "total_iterations": len(self._history),
            "seen_repair_fingerprints_count": len(self._seen_repair_fingerprints),
            "seen_attack_fingerprints_count": len(self._seen_attack_fingerprints),
            "history": [
                {
                    "iteration": h.iteration_index,
                    "state": h.state.value,
                    "before": h.vulnerability_count_before,
                    "after": h.vulnerability_count_after,
                    "new_vulns": h.new_vulnerability_count,
                    "repair_fp": h.repair_fingerprint,
                }
                for h in self._history
            ],
        }
