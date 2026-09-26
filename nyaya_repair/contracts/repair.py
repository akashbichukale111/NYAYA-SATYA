"""Legal grounding and authority reference contracts for NYAYA-SATYA.

Defines LegalGrounding, LegalAuthorityRef, and verification statuses.
Ensures that LLM-generated citations are never automatically marked verified.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class LegalGroundingStatus(str, Enum):
    """Status of legal authority grounding."""

    VERIFIED_AUTHORITY = "VERIFIED_AUTHORITY"
    AUTHORITY_REFERENCE_PRESENT = "AUTHORITY_REFERENCE_PRESENT"
    AUTHORITY_UNVERIFIED = "AUTHORITY_UNVERIFIED"
    AUTHORITY_MISSING = "AUTHORITY_MISSING"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    LEGAL_GROUNDING_UNRESOLVED = "LEGAL_GROUNDING_UNRESOLVED"


class AuthorityType(str, Enum):
    """Type of legal authority."""

    STATUTE = "STATUTE"
    JUDICIAL_PRECEDENT = "JUDICIAL_PRECEDENT"
    REGULATION = "REGULATION"
    CONSTITUTIONAL_PROVISION = "CONSTITUTIONAL_PROVISION"
    TREATISE_SECONDARY = "TREATISE_SECONDARY"
    PROCEDURAL_RULE = "PROCEDURAL_RULE"
    OTHER = "OTHER"


@dataclass(frozen=True)
class LegalAuthorityRef:
    """An explicit legal authority citation linked to a proposition."""

    authority_id: str
    citation: str
    authority_type: AuthorityType
    jurisdiction: str
    status: LegalGroundingStatus = LegalGroundingStatus.AUTHORITY_UNVERIFIED
    verification_source: str | None = None
    pinpoint_reference: str | None = None
    notes: str = ""
    provenance_refs: tuple[ProvenanceRef, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.authority_id or not self.authority_id.strip():
            raise ValueError("authority_id cannot be blank")
        if not self.citation or not self.citation.strip():
            raise ValueError("citation cannot be blank")
        if not re.fullmatch(r"^[a-zA-Z0-9_\-\.]+$", self.authority_id):
            raise ValueError(f"Invalid authority_id format: {self.authority_id!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "citation": self.citation,
            "authority_type": self.authority_type.value,
            "jurisdiction": self.jurisdiction,
            "status": self.status.value,
            "verification_source": self.verification_source,
            "pinpoint_reference": self.pinpoint_reference,
            "notes": self.notes,
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegalAuthorityRef:
        d = dict(data)
        if isinstance(d.get("authority_type"), str):
            d["authority_type"] = AuthorityType(d["authority_type"])
        if isinstance(d.get("status"), str):
            d["status"] = LegalGroundingStatus(d["status"])
        if "provenance_refs" in d:
            d["provenance_refs"] = tuple(
                ProvenanceRef.from_dict(p) if isinstance(p, dict) else p
                for p in d["provenance_refs"]
            )
        return cls(**d)


@dataclass
class LegalGrounding:
    """Evaluation of legal grounding for a claim, issue, or repair."""

    grounding_id: str
    case_id: str
    target_id: str  # claim_id, issue_id, or repair_id
    status: LegalGroundingStatus
    authorities: list[LegalAuthorityRef] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    explanation: str = ""
    assessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.grounding_id or not self.grounding_id.strip():
            raise ValueError("grounding_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        return {
            "grounding_id": self.grounding_id,
            "case_id": self.case_id,
            "target_id": self.target_id,
            "status": self.status.value,
            "authorities": [a.to_dict() for a in self.authorities],
            "unresolved_questions": self.unresolved_questions,
            "explanation": self.explanation,
            "assessed_at": self.assessed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LegalGrounding:
        d = dict(data)
        if isinstance(d.get("status"), str):
            d["status"] = LegalGroundingStatus(d["status"])
        if "authorities" in d:
            d["authorities"] = [
                LegalAuthorityRef.from_dict(a) if isinstance(a, dict) else a
                for a in d["authorities"]
            ]
        if isinstance(d.get("assessed_at"), str):
            d["assessed_at"] = datetime.fromisoformat(d["assessed_at"])
        return cls(**d)
