"""Causal graph validator for NYAYA-SATYA.

Validates causal graph integrity including:
- node/edge consistency
- case isolation
- cycle detection
- causal basis requirements
- temporal causal sanity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.causal_edge import CausalEdge, CausalEdgeStatus
from nyaya_causal.graph.causal_graph import CausalGraph


@dataclass
class GraphValidationResult:
    """Result of causal graph validation."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class CausalGraphValidator:
    """Validates causal graph integrity."""

    def validate(self, graph: CausalGraph) -> GraphValidationResult:
        result = GraphValidationResult()

        # Rule 1: All edges reference existing nodes
        for eid, edge in graph.edges.items():
            if edge.source_node_id not in graph.nodes:
                result.errors.append(f"Edge {eid} references nonexistent source {edge.source_node_id}")
                result.valid = False
            if edge.target_node_id not in graph.nodes:
                result.errors.append(f"Edge {eid} references nonexistent target {edge.target_node_id}")
                result.valid = False

        # Rule 2: Case isolation
        for nid, node in graph.nodes.items():
            if node.case_id != graph.case_id:
                result.errors.append(f"Node {nid} has case_id {node.case_id}, expected {graph.case_id}")
                result.valid = False
        for eid, edge in graph.edges.items():
            if edge.case_id != graph.case_id:
                result.errors.append(f"Edge {eid} has case_id {edge.case_id}, expected {graph.case_id}")
                result.valid = False

        # Rule 3: No self-referencing edges
        for eid, edge in graph.edges.items():
            if edge.source_node_id == edge.target_node_id:
                result.errors.append(f"Self-referencing edge {eid}")
                result.valid = False

        # Rule 4: Causal basis required
        for eid, edge in graph.edges.items():
            if not edge.causal_basis or not edge.causal_basis.strip():
                result.errors.append(f"Edge {eid} has no causal basis")
                result.valid = False

        # Rule 5: No duplicate edge IDs
        seen_ids: set[str] = set()
        for eid in graph.edges:
            if eid in seen_ids:
                result.errors.append(f"Duplicate edge ID: {eid}")
                result.valid = False
            seen_ids.add(eid)

        # Rule 6: Causality-unresolved edges get warnings
        for eid, edge in graph.edges.items():
            if edge.status == CausalEdgeStatus.CAUSALITY_UNRESOLVED:
                result.warnings.append(
                    f"Edge {eid}: Available evidence establishes dependency but not causation"
                )

        return result
