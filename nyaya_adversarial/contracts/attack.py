"""Attack contracts for NYAYA-SATYA Adversarial Gauntlet.

Defines structured AttackScenario, AttackType, and specialized attack result structures.
Strictly non-adjudicative: attack scenarios test structural and factual robustness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class AttackType(str, Enum):
    EVIDENCE_ATTACK = "EVIDENCE_ATTACK"
    CONTRADICTION_ATTACK = "CONTRADICTION_ATTACK"
    TIMELINE_ATTACK = "TIMELINE_ATTACK"
    DEPENDENCY_ATTACK = "DEPENDENCY_ATTACK"
    SOURCE_ATTACK = "SOURCE_ATTACK"
    IDENTITY_ATTACK = "IDENTITY_ATTACK"
    ASSUMPTION_ATTACK = "ASSUMPTION_ATTACK"
    COMPLETENESS_ATTACK = "COMPLETENESS_ATTACK"
    PROCEDURAL_DEPENDENCY_ATTACK = "PROCEDURAL_DEPENDENCY_ATTACK"
    PROMPT_INJECTION_ATTACK = "PROMPT_INJECTION_ATTACK"


class AttackStatus(str, Enum):
    GENERATED = "GENERATED"
    EXECUTED = "EXECUTED"
    EVALUATED = "EVALUATED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass
class AttackScenario:
    """A structured, reproducible attack scenario challenging the Case Digital Twin."""

    attack_id: str
    case_id: str
    attack_type: AttackType
    target_node_id: str
    target_node_type: str  # "CLAIM", "EVIDENCE", "EVENT", "ISSUE", "ASSUMPTION", "SYSTEM"
    premise: str
    attack_question: str
    required_evidence: list[str] = field(default_factory=list)
    expected_observation: str = ""
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    executor: str = "TARKA_GAUNTLET_DETERMINISTIC_ENGINE"
    status: AttackStatus = AttackStatus.GENERATED
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.attack_id or not self.attack_id.strip():
            raise ValueError("attack_id cannot be blank")
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be blank")
        if not self.target_node_id or not self.target_node_id.strip():
            raise ValueError("target_node_id cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["attack_type"] = self.attack_type.value
        data["status"] = self.status.value
        data["generated_at"] = self.generated_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttackScenario:
        d = dict(data)
        if isinstance(d.get("attack_type"), str):
            d["attack_type"] = AttackType(d["attack_type"])
        if isinstance(d.get("status"), str):
            d["status"] = AttackStatus(d["status"])
        if isinstance(d.get("generated_at"), str):
            d["generated_at"] = datetime.fromisoformat(d["generated_at"])
        if d.get("provenance_refs"):
            d["provenance_refs"] = [
                p if isinstance(p, ProvenanceRef) else ProvenanceRef.from_dict(p)
                for p in d["provenance_refs"]
            ]
        return cls(**d)


@dataclass
class EvidenceAttackResult:
    """Outcome of an evidence-targeted attack."""

    target_claim: str
    attack_vector: str
    affected_evidence: list[str]
    evidence_gap: str
    confidence: float
    uncertainty: float
    provenance: list[ProvenanceRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["provenance"] = [p.to_dict() for p in self.provenance]
        return data


@dataclass
class TemporalAttackResult:
    """Outcome of a timeline-targeted attack."""

    event_a: str
    event_b: str
    relationship: str
    conflict: str
    evidence_refs: list[str]
    temporal_precision: str
    uncertainty: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
