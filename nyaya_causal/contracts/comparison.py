"""Before/After comparison contracts for NYAYA-SATYA Counterfactual Lab.

Structured comparison between base and counterfactual scenario outputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


@dataclass
class CounterfactualComparison:
    """Structured before/after comparison of two scenario states."""

    comparison_id: str
    base_scenario_id: str
    counterfactual_scenario_id: str
    changed_nodes: list[dict[str, Any]] = field(default_factory=list)
    unchanged_nodes: list[str] = field(default_factory=list)
    added_relationships: list[str] = field(default_factory=list)
    removed_relationships: list[str] = field(default_factory=list)
    changed_claim_states: list[dict[str, Any]] = field(default_factory=list)
    changed_issue_states: list[dict[str, Any]] = field(default_factory=list)
    changed_timeline_relations: list[dict[str, Any]] = field(default_factory=list)
    new_contradictions: list[dict[str, Any]] = field(default_factory=list)
    resolved_contradictions: list[dict[str, Any]] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def comparison_hash(self) -> str:
        payload = {
            "comparison_id": self.comparison_id,
            "base_scenario_id": self.base_scenario_id,
            "counterfactual_scenario_id": self.counterfactual_scenario_id,
            "changed_nodes": sorted([str(n) for n in self.changed_nodes]),
            "unchanged_nodes": sorted(self.unchanged_nodes),
        }
        return compute_sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["comparison_hash"] = self.comparison_hash
        data["created_at"] = self.created_at.isoformat()
        data["provenance_refs"] = [p.to_dict() for p in self.provenance_refs]
        return data
