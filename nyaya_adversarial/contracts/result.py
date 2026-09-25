"""Finding and result contracts for NYAYA-SATYA Adversarial Gauntlet.

Defines AdversarialFinding, FindingType, and the master AdversarialGauntletReport.
Strictly non-adjudicative: findings describe structural vulnerabilities, not verdicts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from nyaya_adversarial.contracts.fragility import StructuralSeverity
from tarka_vyuh.contracts.provenance import ProvenanceRef


class FindingType(str, Enum):
    FRAGILE_EVIDENCE = "FRAGILE_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    TIMELINE_CONFLICT = "TIMELINE_CONFLICT"
    DEPENDENCY_EXPOSURE = "DEPENDENCY_EXPOSURE"
    SINGLE_SOURCE_DEPENDENCY = "SINGLE_SOURCE_DEPENDENCY"
    PROVENANCE_GAP = "PROVENANCE_GAP"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    ASSUMPTION_EXPOSED = "ASSUMPTION_EXPOSED"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class AdversarialFinding:
    """A discrete vulnerability or stress point identified during adversarial testing."""

    finding_id: str
    case_id: str
    attack_id: str | None
    finding_type: FindingType
    target_id: str
    severity: StructuralSeverity
    structural_impact: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    issue_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    uncertainty: float = 0.5  # [0.0, 1.0]
    explanation: str = ""
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    engine_version: str = "4.0.0"
    status: str = "PENDING_HUMAN_REVIEW"
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.finding_id or not self.finding_id.strip():
            raise ValueError("finding_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not (0.0 <= self.uncertainty <= 1.0):
            raise ValueError(f"uncertainty must be in [0.0, 1.0], got {self.uncertainty}")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["finding_type"] = self.finding_type.value
        data["severity"] = self.severity.value
        data["detected_at"] = self.detected_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdversarialFinding:
        d = dict(data)
        if isinstance(d.get("finding_type"), str):
            d["finding_type"] = FindingType(d["finding_type"])
        if isinstance(d.get("severity"), str):
            d["severity"] = StructuralSeverity(d["severity"])
        if isinstance(d.get("detected_at"), str):
            d["detected_at"] = datetime.fromisoformat(d["detected_at"])
        if d.get("provenance_refs"):
            d["provenance_refs"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance_refs"]
            ]
        return cls(**d)


@dataclass
class AdversarialGauntletReport:
    """Master report compiling all findings, metrics, and stress results."""

    report_id: str
    case_id: str
    twin_hash: str
    findings: list[AdversarialFinding] = field(default_factory=list)
    total_attacks_executed: int = 0
    critical_findings_count: int = 0
    high_findings_count: int = 0
    medium_findings_count: int = 0
    low_findings_count: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "AWAITING_LEGAL_GATE"

    def __post_init__(self) -> None:
        self.critical_findings_count = sum(1 for f in self.findings if f.severity == StructuralSeverity.CRITICAL)
        self.high_findings_count = sum(1 for f in self.findings if f.severity == StructuralSeverity.HIGH)
        self.medium_findings_count = sum(1 for f in self.findings if f.severity == StructuralSeverity.MEDIUM)
        self.low_findings_count = sum(1 for f in self.findings if f.severity == StructuralSeverity.LOW)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "case_id": self.case_id,
            "twin_hash": self.twin_hash,
            "findings": [f.to_dict() for f in self.findings],
            "total_attacks_executed": self.total_attacks_executed,
            "critical_findings_count": self.critical_findings_count,
            "high_findings_count": self.high_findings_count,
            "medium_findings_count": self.medium_findings_count,
            "low_findings_count": self.low_findings_count,
            "generated_at": self.generated_at.isoformat(),
            "status": self.status,
        }
