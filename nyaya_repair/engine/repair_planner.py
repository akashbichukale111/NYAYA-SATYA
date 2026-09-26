"""Repair candidate planner and prioritization engine for NYAYA-SATYA Auto-Healer.
"""

from __future__ import annotations

from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate, RepairChangeType


class RepairPlanner:
    """Prioritizes and sequences repair candidates based on impact and safety."""

    # Higher score = higher priority
    _CHANGE_TYPE_PRIORITY: dict[RepairChangeType, int] = {
        RepairChangeType.ADD_EVIDENCE_REFERENCE: 100,
        RepairChangeType.ADD_PROVENANCE: 90,
        RepairChangeType.QUALIFY_ASSERTION: 80,
        RepairChangeType.CORRECT_TIMELINE_REFERENCE: 70,
        RepairChangeType.REQUEST_MISSING_EVIDENCE: 60,
        RepairChangeType.MARK_UNCERTAIN: 50,
        RepairChangeType.CORRECT_ENTITY_REFERENCE: 40,
        RepairChangeType.SPLIT_COMPOUND_CLAIM: 30,
        RepairChangeType.REPLACE_UNSUPPORTED_CLAIM: 20,
        RepairChangeType.REMOVE_UNSUPPORTED_ASSERTION: 15,
        RepairChangeType.REMOVE_IRRELEVANT_FACT: 10,
        RepairChangeType.ADD_AUTHORITY_REFERENCE: 5,
    }

    def prioritize_repairs(
        self, repairs: list[RepairCandidate]
    ) -> list[RepairCandidate]:
        """Sort repair candidates by structural priority."""
        def score(candidate: RepairCandidate) -> tuple[int, int, str]:
            type_score = self._CHANGE_TYPE_PRIORITY.get(candidate.change_type, 0)
            evidence_bonus = 20 if candidate.evidence_refs else 0
            risk_penalty = -30 if candidate.risk_flags else 0
            total_priority = type_score + evidence_bonus + risk_penalty
            # Secondary sort: fewer risk flags, deterministic ID
            return (total_priority, -len(candidate.risk_flags), candidate.repair_id)

        return sorted(repairs, key=score, reverse=True)
