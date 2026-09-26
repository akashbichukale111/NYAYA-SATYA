"""Perturbation scenario and outcome models for NYAYA-SATYA Legal Perturbation Lab.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class PerturbationType(str, Enum):
    """Categorical class of perturbation experiment."""

    SHOULD_CHANGE = "SHOULD_CHANGE"
    SHOULD_NOT_CHANGE = "SHOULD_NOT_CHANGE"


class PerturbationResultType(str, Enum):
    """Result of comparing expected vs observed structural propagation."""

    EXPECTED_CHANGE = "EXPECTED_CHANGE"
    EXPECTED_NO_CHANGE = "EXPECTED_NO_CHANGE"
    UNEXPECTED_CHANGE = "UNEXPECTED_CHANGE"
    EXPECTED_CHANGE_MISSING = "EXPECTED_CHANGE_MISSING"
    UNKNOWN = "UNKNOWN"


@dataclass
class PerturbationScenario:
    """A controlled structural perturbation experiment to test case stability."""

    scenario_id: str
    case_id: str
    perturbation_type: PerturbationType
    target_node_id: str
    target_node_type: str  # EVIDENCE, CLAIM, EVENT, ENTITY, METADATA
    operation: str  # REMOVE, MODIFY, CORRUPT_TIMESTAMP, INJECT_IRRELEVANT_FACT
    expected_affected_nodes: list[str] = field(default_factory=list)
    protected_nodes: list[str] = field(default_factory=list)
    rationale: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def fingerprint(self) -> str:
        """Deterministic fingerprint of the scenario parameters."""
        payload = {
            "case_id": self.case_id,
            "type": self.perturbation_type.value,
            "target": self.target_node_id,
            "operation": self.operation,
            "expected": sorted(self.expected_affected_nodes),
            "protected": sorted(self.protected_nodes),
        }
        dumped = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "case_id": self.case_id,
            "perturbation_type": self.perturbation_type.value,
            "target_node_id": self.target_node_id,
            "target_node_type": self.target_node_type,
            "operation": self.operation,
            "expected_affected_nodes": list(self.expected_affected_nodes),
            "protected_nodes": list(self.protected_nodes),
            "rationale": self.rationale,
            "parameters": self.parameters,
            "fingerprint": self.fingerprint,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PerturbationOutcome:
    """Detailed result of running a perturbation experiment."""

    scenario_id: str
    case_id: str
    result_type: PerturbationResultType
    is_safe: bool
    observed_affected_nodes: list[str] = field(default_factory=list)
    missing_expected_changes: list[str] = field(default_factory=list)
    unexpected_changes: list[str] = field(default_factory=list)
    explanation: str = ""
    pre_hash: str = ""
    post_hash: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "case_id": self.case_id,
            "result_type": self.result_type.value,
            "is_safe": self.is_safe,
            "observed_affected_nodes": list(self.observed_affected_nodes),
            "missing_expected_changes": list(self.missing_expected_changes),
            "unexpected_changes": list(self.unexpected_changes),
            "explanation": self.explanation,
            "pre_hash": self.pre_hash,
            "post_hash": self.post_hash,
            "evaluated_at": self.evaluated_at.isoformat(),
        }
