"""Case Digital Twin Adapter for NYAYA-SATYA Adversarial Subsystem.

Provides read-only extraction and snapshot access to CaseDigitalTwin.
Enforces cross-case boundary validation.
"""

from __future__ import annotations

import copy
from typing import Any

from nyaya_twin.contracts.case_twin import CaseDigitalTwin, compute_twin_hash


class TwinAdversarialAdapter:
    """Safe read-only adapter interfacing between CaseDigitalTwin and adversarial engines."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self._twin = twin
        self._case_id = twin.case_id

    @property
    def case_id(self) -> str:
        return self._case_id

    def verify_case_ownership(self, target_case_id: str) -> None:
        """Enforces cross-case boundary security."""
        if self._case_id != target_case_id:
            raise ValueError(
                f"Cross-case boundary violation: adapter is bound to {self._case_id}, "
                f"but request targeted {target_case_id}."
            )

    def get_simulation_copy(self) -> CaseDigitalTwin:
        """Returns an isolated, deep-copied simulation twin."""
        return copy.deepcopy(self._twin)

    def get_current_hash(self) -> str:
        """Returns deterministic hash of the underlying twin."""
        return compute_twin_hash(self._twin)

    def extract_summary_stats(self) -> dict[str, Any]:
        """Extracts high-level graph metrics for adversarial stress testing."""
        return {
            "case_id": self._case_id,
            "entities_count": len(self._twin.entities),
            "claims_count": len(self._twin.claims),
            "issues_count": len(self._twin.issues),
            "events_count": len(self._twin.events),
            "evidence_count": len(self._twin.evidence_refs),
            "relationships_count": len(self._twin.relationships),
            "contradictions_count": len(self._twin.contradictions),
            "temporal_conflicts_count": len(self._twin.temporal_conflicts),
        }
