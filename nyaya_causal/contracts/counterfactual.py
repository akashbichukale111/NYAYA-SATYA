"""Counterfactual scenario result contracts for NYAYA-SATYA.

Represents the result of running a counterfactual scenario, including
the blast-radius report and effect classification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_causal.contracts.effect import CausalEffect
from tarka_vyuh.contracts.provenance import ProvenanceRef, compute_sha256


@dataclass
class BlastRadiusReport:
    """Report on the structural blast-radius of an intervention."""

    report_id: str
    case_id: str
    target_id: str
    target_type: str
    intervention_summary: str
    direct_effects: list[CausalEffect] = field(default_factory=list)
    indirect_effects: list[CausalEffect] = field(default_factory=list)
    unaffected_nodes: list[str] = field(default_factory=list)
    newly_unresolved: list[str] = field(default_factory=list)
    newly_supported: list[str] = field(default_factory=list)
    newly_contradicted: list[str] = field(default_factory=list)
    broken_dependencies: list[str] = field(default_factory=list)
    preserved_dependencies: list[str] = field(default_factory=list)
    affected_issues: list[str] = field(default_factory=list)
    affected_claims: list[str] = field(default_factory=list)
    provenance_refs: list[ProvenanceRef] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def scenario_hash(self) -> str:
        payload = {
            "report_id": self.report_id,
            "case_id": self.case_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "direct_effects": sorted([e.node_id for e in self.direct_effects]),
            "indirect_effects": sorted([e.node_id for e in self.indirect_effects]),
            "unaffected_nodes": sorted(self.unaffected_nodes),
        }
        return compute_sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "report_id": self.report_id,
            "case_id": self.case_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "intervention_summary": self.intervention_summary,
            "direct_effects": [e.to_dict() for e in self.direct_effects],
            "indirect_effects": [e.to_dict() for e in self.indirect_effects],
            "unaffected_nodes": self.unaffected_nodes,
            "newly_unresolved": self.newly_unresolved,
            "newly_supported": self.newly_supported,
            "newly_contradicted": self.newly_contradicted,
            "broken_dependencies": self.broken_dependencies,
            "preserved_dependencies": self.preserved_dependencies,
            "affected_issues": self.affected_issues,
            "affected_claims": self.affected_claims,
            "scenario_hash": self.scenario_hash,
            "created_at": self.created_at.isoformat(),
            "provenance_refs": [p.to_dict() for p in self.provenance_refs],
        }
        return data
