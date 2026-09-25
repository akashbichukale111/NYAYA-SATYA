"""Reasoning Proposal Contract for TARKA-VYUH.

Defines the strongly typed proposal object produced by the adversarial reasoning
engine and submitted to UNWIND Core for governance evaluation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef


class ProposalStatus(str, Enum):
    PROPOSED = "PROPOSED"
    GOVERNANCE_REVIEW = "GOVERNANCE_REVIEW"
    ASK_HUMAN = "ASK_HUMAN"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class ReasoningType(str, Enum):
    CONTRADICTION_ANALYSIS = "CONTRADICTION_ANALYSIS"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    CAUSAL_ANALYSIS = "CAUSAL_ANALYSIS"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    REPAIR_PROPOSAL = "REPAIR_PROPOSAL"
    ADVERSARIAL_CHALLENGE = "ADVERSARIAL_CHALLENGE"


@dataclass(frozen=True)
class ProposedAction:
    """Action proposed by the reasoning engine, subject to human approval."""

    action_type: str
    target_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    is_consequential: bool = True

    def __post_init__(self) -> None:
        if not self.action_type or not self.action_type.strip():
            raise ValueError("action_type cannot be empty")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("target_id cannot be empty")


@dataclass
class ReasoningProposal:
    """The central analytical proposal emitted by TARKA-VYUH.

    TARKA-VYUH generates proposals; it NEVER executes them.
    """

    proposal_id: str
    case_id: str
    reasoning_type: ReasoningType
    input_evidence_ids: list[str]
    claims: list[str]
    assumptions: list[str]
    uncertainty: float  # [0.0, 1.0]
    proposed_action: ProposedAction
    provenance_refs: list[ProvenanceRef]
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    model_metadata: dict[str, Any] = field(default_factory=dict)
    status: ProposalStatus = ProposalStatus.PROPOSED
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        # Validate proposal_id
        if not self.proposal_id or not self.proposal_id.strip():
            raise ValueError("proposal_id cannot be empty")
        if len(self.proposal_id) > 128:
            raise ValueError("proposal_id exceeds maximum length of 128 characters")

        # Validate case_id
        if not self.case_id or not self.case_id.strip():
            raise ValueError("case_id cannot be empty")
        if len(self.case_id) > 128:
            raise ValueError("case_id exceeds maximum length of 128 characters")

        # Validate reasoning_type
        if not isinstance(self.reasoning_type, ReasoningType):
            if isinstance(self.reasoning_type, str):
                try:
                    self.reasoning_type = ReasoningType(self.reasoning_type)
                except ValueError as err:
                    raise ValueError(f"Invalid reasoning_type: {self.reasoning_type}") from err
            else:
                raise ValueError(f"reasoning_type must be a ReasoningType enum, got {type(self.reasoning_type)}")

        # Validate status
        if not isinstance(self.status, ProposalStatus):
            if isinstance(self.status, str):
                try:
                    self.status = ProposalStatus(self.status)
                except ValueError as err:
                    raise ValueError(f"Invalid status: {self.status}") from err
            else:
                raise ValueError(f"status must be a ProposalStatus enum, got {type(self.status)}")

        # Validate input evidence
        if not self.input_evidence_ids or not isinstance(self.input_evidence_ids, list):
            raise ValueError("input_evidence_ids must be a non-empty list of identifiers")
        for eid in self.input_evidence_ids:
            if not isinstance(eid, str) or not eid.strip():
                raise ValueError("All input_evidence_ids must be non-empty strings")

        # Validate claims
        if not self.claims or not isinstance(self.claims, list):
            raise ValueError("claims must be a non-empty list of statements")
        for c in self.claims:
            if not isinstance(c, str) or not c.strip():
                raise ValueError("All claims must be non-empty strings")
            if len(c) > 10000:
                raise ValueError("Single claim exceeds max length limit of 10000 chars")

        # Validate assumptions
        if not isinstance(self.assumptions, list):
            raise ValueError("assumptions must be a list of strings")

        # Validate uncertainty range
        if not isinstance(self.uncertainty, (int, float)) or isinstance(self.uncertainty, bool):
            raise ValueError("uncertainty must be a float between 0.0 and 1.0")
        if not 0.0 <= float(self.uncertainty) <= 1.0:
            raise ValueError(f"uncertainty must be in [0.0, 1.0], got {self.uncertainty}")

        # Validate proposed_action
        if not isinstance(self.proposed_action, ProposedAction):
            if isinstance(self.proposed_action, dict):
                self.proposed_action = ProposedAction(**self.proposed_action)
            else:
                raise ValueError("proposed_action must be an instance of ProposedAction")

        # Validate provenance_refs
        if not self.provenance_refs or not isinstance(self.provenance_refs, list):
            raise ValueError("provenance_refs must be a non-empty list of ProvenanceRef objects")
        for pref in self.provenance_refs:
            if not isinstance(pref, ProvenanceRef):
                raise ValueError("All elements in provenance_refs must be ProvenanceRef instances")

    def compute_hash(self) -> str:
        """Deterministic fingerprint of the proposal's core content.

        Used to detect any modification after approval.
        """
        payload = {
            "proposal_id": self.proposal_id,
            "case_id": self.case_id,
            "reasoning_type": self.reasoning_type.value,
            "input_evidence_ids": sorted(self.input_evidence_ids),
            "claims": sorted(self.claims),
            "assumptions": sorted(self.assumptions),
            "uncertainty": round(float(self.uncertainty), 6),
            "proposed_action": asdict(self.proposed_action),
            "provenance_hashes": sorted(p.content_hash for p in self.provenance_refs),
            "schema_version": self.schema_version,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize proposal to JSON-compatible dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "case_id": self.case_id,
            "reasoning_type": self.reasoning_type.value,
            "input_evidence_ids": list(self.input_evidence_ids),
            "claims": list(self.claims),
            "assumptions": list(self.assumptions),
            "uncertainty": self.uncertainty,
            "proposed_action": asdict(self.proposed_action),
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
            "generated_at": self.generated_at.isoformat(),
            "model_metadata": dict(self.model_metadata),
            "status": self.status.value,
            "schema_version": self.schema_version,
            "content_hash": self.compute_hash(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReasoningProposal:
        """Deserialize proposal from dictionary."""
        raw = dict(data)
        raw.pop("content_hash", None)
        action_data = raw.pop("proposed_action")
        action = ProposedAction(**action_data) if isinstance(action_data, dict) else action_data
        
        prov_list = []
        for p in raw.pop("provenance_refs", []):
            if isinstance(p, dict):
                p_copy = dict(p)
                p_copy["created_at"] = datetime.fromisoformat(p_copy["created_at"])
                prov_list.append(ProvenanceRef(**p_copy))
            else:
                prov_list.append(p)

        gen_at = raw.pop("generated_at")
        if isinstance(gen_at, str):
            gen_at = datetime.fromisoformat(gen_at)

        return cls(
            proposed_action=action,
            provenance_refs=prov_list,
            generated_at=gen_at,
            reasoning_type=ReasoningType(raw.pop("reasoning_type")),
            status=ProposalStatus(raw.pop("status", ProposalStatus.PROPOSED.value)),
            **raw,
        )


__all__ = [
    "ProposedAction",
    "ProposalStatus",
    "ReasoningProposal",
    "ReasoningType",
]
