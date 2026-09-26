"""Repair action primitives for NYAYA-SATYA Auto-Healer.

Defines atomic actions that can be simulated on a cloned CaseDigitalTwin.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ActionPrimitive(str, Enum):
    """Primitive operations performed on a digital twin copy."""

    ATTACH_EVIDENCE_TO_CLAIM = "ATTACH_EVIDENCE_TO_CLAIM"
    DETACH_EVIDENCE_FROM_CLAIM = "DETACH_EVIDENCE_FROM_CLAIM"
    UPDATE_CLAIM_STATUS = "UPDATE_CLAIM_STATUS"
    UPDATE_CLAIM_PREDICATE = "UPDATE_CLAIM_PREDICATE"
    UPDATE_CLAIM_OBJECT = "UPDATE_CLAIM_OBJECT"
    SPLIT_CLAIM = "SPLIT_CLAIM"
    REMOVE_CLAIM = "REMOVE_CLAIM"
    ATTACH_AUTHORITY_TO_ISSUE = "ATTACH_AUTHORITY_TO_ISSUE"
    UPDATE_EVENT_TIME = "UPDATE_EVENT_TIME"
    UPDATE_ENTITY_ALIAS = "UPDATE_ENTITY_ALIAS"
    ADD_PROVENANCE_REF = "ADD_PROVENANCE_REF"
    FLAG_FOR_EVIDENCE_REQUEST = "FLAG_FOR_EVIDENCE_REQUEST"


@dataclass(frozen=True)
class RepairAction:
    """An atomic, executable mutation applied solely to a simulated twin copy."""

    action_id: str
    primitive: ActionPrimitive
    target_id: str  # claim_id, event_id, issue_id, etc.
    parameters: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.action_id or not self.action_id.strip():
            raise ValueError("action_id cannot be blank")
        if not self.target_id or not self.target_id.strip():
            raise ValueError("target_id cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "primitive": self.primitive.value,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairAction:
        d = dict(data)
        if isinstance(d.get("primitive"), str):
            d["primitive"] = ActionPrimitive(d["primitive"])
        return cls(**d)
