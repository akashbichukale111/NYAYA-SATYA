"""Admissibility readiness and certification safety contracts for NYAYA-SATYA.

Strictly non-adjudicative:
- Uses 'ADMISSIBILITY_READINESS_GATE', never 'Evidence legally admissible'.
- Uses 'CERTIFICATION_PENDING_HUMAN_SIGNATURE'.
- Never claims AI has legally certified evidence or signed BSA certificates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class AdmissibilityGateStatus(str, Enum):
    """Status under the Admissibility Readiness Gate."""

    READINESS_CHECK_PASSED = "READINESS_CHECK_PASSED"
    CERTIFICATION_PENDING_HUMAN_SIGNATURE = "CERTIFICATION_PENDING_HUMAN_SIGNATURE"
    PROVENANCE_INCOMPLETE = "PROVENANCE_INCOMPLETE"
    HASH_VERIFICATION_FAILED = "HASH_VERIFICATION_FAILED"
    CHAIN_OF_CUSTODY_UNRESOLVED = "CHAIN_OF_CUSTODY_UNRESOLVED"
    EXCLUSIONARY_RULE_FLAGGED = "EXCLUSIONARY_RULE_FLAGGED"


@dataclass
class AdmissibilityReadinessGate:
    """Evaluates whether an electronic record satisfies structural criteria for admission.

    IMPORTANT: Does NOT legally certify or admit the record.
    Final legal certification requires an authorized human signature under relevant statutes.
    """

    gate_id: str
    evidence_id: str
    case_id: str
    status: AdmissibilityGateStatus
    has_unbroken_provenance: bool
    has_matching_raw_hash: bool
    has_sanitization_audit: bool
    audit_notes: list[str] = field(default_factory=list)
    human_signatory_required: bool = True
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "evidence_id": self.evidence_id,
            "case_id": self.case_id,
            "status": self.status.value,
            "has_unbroken_provenance": self.has_unbroken_provenance,
            "has_matching_raw_hash": self.has_matching_raw_hash,
            "has_sanitization_audit": self.has_sanitization_audit,
            "audit_notes": list(self.audit_notes),
            "human_signatory_required": self.human_signatory_required,
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdmissibilityReadinessGate:
        d = dict(data)
        if isinstance(d.get("status"), str):
            d["status"] = AdmissibilityGateStatus(d["status"])
        if "provenance_refs" in d:
            d["provenance_refs"] = [
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            ]
        if isinstance(d.get("evaluated_at"), str):
            d["evaluated_at"] = datetime.fromisoformat(d["evaluated_at"])
        return cls(**d)
