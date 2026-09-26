"""Repair candidate contracts for NYAYA-SATYA Auto-Healer.

Defines RepairCandidate, RepairChangeType, and RepairCandidateStatus.
Every repair candidate is traceable, verifiable, and strictly evidence-grounded.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_repair.contracts.repair import LegalAuthorityRef
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


class RepairChangeType(str, Enum):
    """Categorical change types for repair operations."""

    ADD_EVIDENCE_REFERENCE = "ADD_EVIDENCE_REFERENCE"
    REMOVE_UNSUPPORTED_ASSERTION = "REMOVE_UNSUPPORTED_ASSERTION"
    QUALIFY_ASSERTION = "QUALIFY_ASSERTION"
    REPLACE_UNSUPPORTED_CLAIM = "REPLACE_UNSUPPORTED_CLAIM"
    CORRECT_TIMELINE_REFERENCE = "CORRECT_TIMELINE_REFERENCE"
    CORRECT_ENTITY_REFERENCE = "CORRECT_ENTITY_REFERENCE"
    ADD_PROVENANCE = "ADD_PROVENANCE"
    ADD_AUTHORITY_REFERENCE = "ADD_AUTHORITY_REFERENCE"
    MARK_UNCERTAIN = "MARK_UNCERTAIN"
    SPLIT_COMPOUND_CLAIM = "SPLIT_COMPOUND_CLAIM"
    REMOVE_IRRELEVANT_FACT = "REMOVE_IRRELEVANT_FACT"
    REQUEST_MISSING_EVIDENCE = "REQUEST_MISSING_EVIDENCE"


class RepairCandidateStatus(str, Enum):
    """Lifecycle status of a repair candidate."""

    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    SIMULATED = "SIMULATED"
    ATTACK_TESTED = "ATTACK_TESTED"
    IMMUNE = "IMMUNE"
    VULNERABLE = "VULNERABLE"
    REJECTED = "REJECTED"
    APPROVED_BY_GATE = "APPROVED_BY_GATE"


def compute_repair_fingerprint(
    *,
    case_id: str,
    target_vulnerability_id: str,
    change_type: str,
    target_claim_id: str | None,
    proposed_change: dict[str, Any],
) -> str:
    """Compute deterministic SHA-256 fingerprint for a repair candidate."""
    payload = {
        "case_id": case_id,
        "target_vulnerability_id": target_vulnerability_id,
        "change_type": change_type,
        "target_claim_id": target_claim_id or "",
        "proposed_change": proposed_change,
    }
    dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


@dataclass
class RepairCandidate:
    """A strongly typed proposed repair addressing an identified vulnerability."""

    repair_id: str
    case_id: str
    target_vulnerability_id: str
    change_type: RepairChangeType
    proposed_change: dict[str, Any]
    target_claim_id: str | None = None
    target_issue_id: str | None = None
    original_state_hash: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    authority_refs: list[LegalAuthorityRef] = field(default_factory=list)
    causal_dependencies: list[str] = field(default_factory=list)
    blast_radius: dict[str, Any] = field(default_factory=dict)
    expected_effects: list[str] = field(default_factory=list)
    expected_unchanged_elements: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    status: RepairCandidateStatus = RepairCandidateStatus.PROPOSED
    rationale: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.repair_id or not self.repair_id.strip():
            raise ValueError("repair_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.repair_id):
            raise ValueError(f"Invalid repair_id format: {self.repair_id!r}")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.case_id):
            raise ValueError(f"Invalid case_id format: {self.case_id!r}")
        if not self.target_vulnerability_id or not self.target_vulnerability_id.strip():
            raise ValueError("target_vulnerability_id cannot be blank")

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint independent of creation timestamp."""
        return compute_repair_fingerprint(
            case_id=self.case_id,
            target_vulnerability_id=self.target_vulnerability_id,
            change_type=self.change_type.value,
            target_claim_id=self.target_claim_id,
            proposed_change=self.proposed_change,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "repair_id": self.repair_id,
            "case_id": self.case_id,
            "target_vulnerability_id": self.target_vulnerability_id,
            "change_type": self.change_type.value,
            "target_claim_id": self.target_claim_id,
            "target_issue_id": self.target_issue_id,
            "original_state_hash": self.original_state_hash,
            "proposed_change": self.proposed_change,
            "evidence_refs": list(self.evidence_refs),
            "authority_refs": [a.to_dict() for a in self.authority_refs],
            "causal_dependencies": list(self.causal_dependencies),
            "blast_radius": self.blast_radius,
            "expected_effects": list(self.expected_effects),
            "expected_unchanged_elements": list(self.expected_unchanged_elements),
            "risk_flags": list(self.risk_flags),
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
            "status": self.status.value,
            "rationale": self.rationale,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairCandidate:
        d = dict(data)
        d.pop("fingerprint", None)
        if isinstance(d.get("change_type"), str):
            d["change_type"] = RepairChangeType(d["change_type"])
        if isinstance(d.get("status"), str):
            d["status"] = RepairCandidateStatus(d["status"])
        if "authority_refs" in d:
            d["authority_refs"] = [
                LegalAuthorityRef.from_dict(a) if isinstance(a, dict) else a
                for a in d["authority_refs"]
            ]
        if "provenance_refs" in d:
            d["provenance_refs"] = [
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            ]
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
        return cls(**d)
