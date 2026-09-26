"""Adversarial adapter for NYAYA-SATYA Causal Reasoning.

Bridges Phase 4 adversarial findings into Phase 5 interventions:
Adversarial Finding -> Intervention -> Counterfactual -> Blast Radius -> Comparison
"""

from __future__ import annotations

import uuid
from typing import Any

from nyaya_causal.contracts.intervention import (
    Intervention,
    InterventionOperation,
    InterventionTargetType,
)


class AdversarialToCausalAdapter:
    """Converts adversarial findings into causal interventions."""

    def achilles_heel_to_intervention(
        self,
        *,
        case_id: str,
        evidence_id: str,
        description: str = "",
    ) -> Intervention:
        """Convert an Achilles-heel finding into an evidence removal intervention."""
        return Intervention(
            intervention_id=f"INT_ACH_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            target_id=evidence_id,
            target_type=InterventionTargetType.EVIDENCE,
            operation=InterventionOperation.REMOVE,
            rationale=f"Achilles-heel analysis: testing case resilience without {evidence_id}. {description}",
        )

    def assumption_to_intervention(
        self,
        *,
        case_id: str,
        assumption_id: str,
        related_claim_ids: list[str] | None = None,
        description: str = "",
    ) -> Intervention:
        """Convert an assumption challenge into a causal intervention."""
        return Intervention(
            intervention_id=f"INT_ASM_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            target_id=assumption_id,
            target_type=InterventionTargetType.ASSUMPTION,
            operation=InterventionOperation.MARK_CONTESTED,
            hypothetical_state={"related_claim_ids": related_claim_ids or []},
            rationale=f"Assumption contestation: testing what if {assumption_id} is false. {description}",
        )

    def fragility_to_intervention(
        self,
        *,
        case_id: str,
        evidence_id: str,
        fragility_score: float = 0.0,
    ) -> Intervention:
        """Convert a fragility finding into an evidence intervention."""
        return Intervention(
            intervention_id=f"INT_FRG_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            target_id=evidence_id,
            target_type=InterventionTargetType.EVIDENCE,
            operation=InterventionOperation.REMOVE,
            rationale=f"Fragility analysis (score={fragility_score:.2f}): simulating evidence loss",
        )

    def missing_evidence_to_gap(
        self,
        *,
        case_id: str,
        claim_id: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Surface a missing evidence finding as a causal gap."""
        return {
            "case_id": case_id,
            "claim_id": claim_id,
            "gap_type": "MISSING_EVIDENCE_FOR_CAUSAL_DISTINCTION",
            "description": description,
            "note": "This evidence gap was identified during adversarial analysis. "
                    "The system does NOT claim such evidence exists.",
        }
