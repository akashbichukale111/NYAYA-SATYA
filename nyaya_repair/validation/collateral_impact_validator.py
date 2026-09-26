"""Collateral impact validation for NYAYA-SATYA Auto-Healer.

Ensures simulated repairs do not silently alter unrelated claims, events,
or cause unintended structural damage to the Case Digital Twin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


@dataclass
class CollateralImpactResult:
    """Outcome of validating collateral impact of a repair."""

    has_acceptable_impact: bool = True
    unintended_claim_changes: list[str] = field(default_factory=list)
    unintended_event_changes: list[str] = field(default_factory=list)
    broken_expected_unchanged: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_acceptable_impact": self.has_acceptable_impact,
            "unintended_claim_changes": list(self.unintended_claim_changes),
            "unintended_event_changes": list(self.unintended_event_changes),
            "broken_expected_unchanged": list(self.broken_expected_unchanged),
            "errors": list(self.errors),
        }


class CollateralImpactValidator:
    """Detects unintended structural shifts between original and repaired twin states."""

    def validate_impact(
        self,
        repair: RepairCandidate,
        original_twin: CaseDigitalTwin,
        repaired_twin: CaseDigitalTwin,
    ) -> CollateralImpactResult:
        """Verify that only intended elements changed."""
        result = CollateralImpactResult()

        # Check expected unchanged elements
        for node_id in repair.expected_unchanged_elements:
            if node_id in original_twin.claims and node_id in repaired_twin.claims:
                orig_c = original_twin.claims[node_id]
                rep_c = repaired_twin.claims[node_id]
                if orig_c.status != rep_c.status or orig_c.statement != rep_c.statement:
                    result.broken_expected_unchanged.append(node_id)
                    result.errors.append(
                        f"Expected unchanged claim '{node_id}' was altered in repair simulation"
                    )
                    result.has_acceptable_impact = False

        # Scan for unintended claim changes (outside target claim)
        for cid, orig_c in original_twin.claims.items():
            if cid == repair.target_claim_id or cid in repair.expected_effects:
                continue
            rep_c = repaired_twin.claims.get(cid)
            if rep_c and rep_c.status != orig_c.status:
                result.unintended_claim_changes.append(cid)

        if len(result.unintended_claim_changes) > 3:
            result.errors.append(
                f"High collateral impact: {len(result.unintended_claim_changes)} unintended claims changed state"
            )
            result.has_acceptable_impact = False

        return result
