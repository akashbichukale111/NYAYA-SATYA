"""Hypothesis Manager for Evidence Conflict Arena.

Generates and maintains plausible competing factual hypotheses for evidentiary conflicts.
Strictly non-adjudicative: never selects a 'winner' or declares a single hypothesis as true.
"""

from __future__ import annotations

from typing import Any

from nyaya_adversarial.contracts.conflict import EvidenceConflict
from nyaya_adversarial.contracts.hypothesis import (
    ConflictHypothesis,
    HypothesisStatus,
)
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class HypothesisManager:
    """Manages competing factual hypotheses for evidentiary conflicts."""

    def __init__(self, twin: CaseDigitalTwin) -> None:
        self.twin = twin
        self.case_id = twin.case_id

    def generate_hypotheses_for_conflict(
        self,
        conflict: EvidenceConflict,
    ) -> list[ConflictHypothesis]:
        """Generates standard four-hypothesis suite (H1..H4) for a material conflict."""
        h1 = ConflictHypothesis(
            hypothesis_id=f"{conflict.conflict_id}_H1",
            conflict_id=conflict.conflict_id,
            case_id=self.case_id,
            description=f"Evidence {conflict.evidence_a_id} is accurate and factual.",
            supporting_evidence_ids=[conflict.evidence_a_id],
            contradicting_evidence_ids=[conflict.evidence_b_id],
            assumptions=[f"Evidence {conflict.evidence_b_id} contains an error, omission, or alternative perspective."],
            unresolved_questions=[f"Why does {conflict.evidence_b_id} contradict {conflict.evidence_a_id}?"],
            provenance_refs=list(conflict.provenance_refs),
            status=HypothesisStatus.PARTIALLY_SUPPORTED,
        )

        h2 = ConflictHypothesis(
            hypothesis_id=f"{conflict.conflict_id}_H2",
            conflict_id=conflict.conflict_id,
            case_id=self.case_id,
            description=f"Evidence {conflict.evidence_b_id} is accurate and factual.",
            supporting_evidence_ids=[conflict.evidence_b_id],
            contradicting_evidence_ids=[conflict.evidence_a_id],
            assumptions=[f"Evidence {conflict.evidence_a_id} contains an error, omission, or alternative perspective."],
            unresolved_questions=[f"Why does {conflict.evidence_a_id} contradict {conflict.evidence_b_id}?"],
            provenance_refs=list(conflict.provenance_refs),
            status=HypothesisStatus.PARTIALLY_SUPPORTED,
        )

        h3 = ConflictHypothesis(
            hypothesis_id=f"{conflict.conflict_id}_H3",
            conflict_id=conflict.conflict_id,
            case_id=self.case_id,
            description=f"Both {conflict.evidence_a_id} and {conflict.evidence_b_id} describe distinct events, times, or transaction scopes.",
            supporting_evidence_ids=[conflict.evidence_a_id, conflict.evidence_b_id],
            contradicting_evidence_ids=[],
            assumptions=["The documents refer to separate scopes that do not directly negate one another."],
            unresolved_questions=["Is there a common timeline or transaction boundary separating both records?"],
            provenance_refs=list(conflict.provenance_refs),
            status=HypothesisStatus.CONTESTED,
        )

        h4 = ConflictHypothesis(
            hypothesis_id=f"{conflict.conflict_id}_H4",
            conflict_id=conflict.conflict_id,
            case_id=self.case_id,
            description="Available record is insufficient to distinguish or reconcile both sources.",
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
            assumptions=["Primary corroborating third-party records are missing."],
            unresolved_questions=["What independent third-party evidence could resolve this disparity?"],
            provenance_refs=list(conflict.provenance_refs),
            status=HypothesisStatus.INSUFFICIENT_EVIDENCE,
        )

        return [h1, h2, h3, h4]

    def build_case_hypothesis_map(
        self,
        conflicts: list[EvidenceConflict],
    ) -> dict[str, list[ConflictHypothesis]]:
        """Maps each conflict_id to its suite of preserved hypotheses."""
        mapping: dict[str, list[ConflictHypothesis]] = {}
        for c in conflicts:
            mapping[c.conflict_id] = self.generate_hypotheses_for_conflict(c)
        return mapping
