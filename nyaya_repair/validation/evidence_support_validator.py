"""Evidence support validation for NYAYA-SATYA Auto-Healer.

Enforces strict evidence grounding:
- No repair may introduce unresolved evidence.
- Missing evidence triggers EVIDENCE_REQUIRED status.
- Blocked/quarantined evidence is strictly prohibited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nyaya_repair.contracts.repair_candidate import RepairCandidate
from nyaya_twin.contracts.case_twin import CaseDigitalTwin


class EvidenceGroundingStatus(str, Enum):
    """Grounding status of evidence in a proposed repair."""

    FULLY_GROUNDED = "FULLY_GROUNDED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    QUARANTINED_EVIDENCE_PROHIBITED = "QUARANTINED_EVIDENCE_PROHIBITED"
    UNRESOLVED_REFERENCE = "UNRESOLVED_REFERENCE"


@dataclass
class EvidenceValidationResult:
    """Outcome of validating evidence references in a repair."""

    is_valid: bool = True
    status: EvidenceGroundingStatus = EvidenceGroundingStatus.FULLY_GROUNDED
    resolved_evidence_ids: list[str] = field(default_factory=list)
    missing_evidence_ids: list[str] = field(default_factory=list)
    blocked_evidence_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status.value,
            "resolved_evidence_ids": list(self.resolved_evidence_ids),
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "blocked_evidence_ids": list(self.blocked_evidence_ids),
            "errors": list(self.errors),
        }


class EvidenceSupportValidator:
    """Validates that all evidence cited by a repair is grounded in the record."""

    def validate_evidence(
        self,
        repair: RepairCandidate,
        twin: CaseDigitalTwin,
    ) -> EvidenceValidationResult:
        """Validate referenced evidence against the canonical CaseDigitalTwin."""
        result = EvidenceValidationResult()

        for ev_id in repair.evidence_refs:
            ref = twin.evidence_refs.get(ev_id)
            if ref is None:
                result.missing_evidence_ids.append(ev_id)
                result.errors.append(
                    f"Evidence '{ev_id}' referenced by repair cannot be resolved. Status: EVIDENCE_REQUIRED"
                )
                result.is_valid = False
                result.status = EvidenceGroundingStatus.EVIDENCE_REQUIRED
            else:
                # Check quarantine status
                if hasattr(ref, "risk_level") and getattr(ref.risk_level, "value", str(ref.risk_level)) == "BLOCKED":
                    result.blocked_evidence_ids.append(ev_id)
                    result.errors.append(
                        f"Quarantined/blocked evidence '{ev_id}' cannot be introduced into repair"
                    )
                    result.is_valid = False
                    result.status = EvidenceGroundingStatus.QUARANTINED_EVIDENCE_PROHIBITED
                else:
                    result.resolved_evidence_ids.append(ev_id)

        # Check for evidence cited inside proposed_change dictionary
        add_ev = repair.proposed_change.get("add_evidence_id")
        if add_ev and add_ev not in result.resolved_evidence_ids and add_ev not in result.missing_evidence_ids:
            if add_ev not in twin.evidence_refs:
                result.missing_evidence_ids.append(add_ev)
                result.errors.append(
                    f"Evidence '{add_ev}' in proposed_change cannot be resolved. Status: EVIDENCE_REQUIRED"
                )
                result.is_valid = False
                result.status = EvidenceGroundingStatus.EVIDENCE_REQUIRED
            else:
                result.resolved_evidence_ids.append(add_ev)

        return result
