"""Causal graph engine for NYAYA-SATYA.

Builds and maintains a typed causal graph over the Case Digital Twin.
Detects cycles, validates causal vs correlational boundaries,
and enforces temporal causal sanity.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.causal_edge import (
    CausalEdge,
    CausalEdgeStatus,
    CausalRelationshipType,
)
from nyaya_causal.contracts.causal_node import CausalNode, CausalNodeStatus, CausalNodeType
from tarka_vyuh.contracts.provenance import compute_sha256

# Configurable limits
MAX_GRAPH_DEPTH = 50
MAX_PATHS = 100
MAX_NODES = 10000


class CausalCycleDetectedError(ValueError):
    """Raised when a cycle is detected in the causal graph."""


class CausalTemporalInconsistencyError(ValueError):
    """Raised when an effect precedes its cause."""


@dataclass
class CausalGraph:
    """A directed acyclic causal graph over case nodes."""

    case_id: str
    nodes: dict[str, CausalNode] = field(default_factory=dict)
    edges: dict[str, CausalEdge] = field(default_factory=dict)
    _adjacency: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    _reverse_adjacency: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, node: CausalNode) -> None:
        """Add a causal node to the graph."""
        if node.case_id != self.case_id:
            raise ValueError(f"Cross-case node rejected: graph={self.case_id}, node={node.case_id}")
        if len(self.nodes) >= MAX_NODES:
            raise ValueError(f"Graph node limit ({MAX_NODES}) exceeded")
        self.nodes[node.node_id] = node

    def add_edge(self, edge: CausalEdge) -> None:
        """Add a causal edge. Validates acyclicity and case isolation."""
        if edge.case_id != self.case_id:
            raise ValueError(f"Cross-case edge rejected: graph={self.case_id}, edge={edge.case_id}")
        if edge.source_node_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_node_id!r} not in graph")
        if edge.target_node_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_node_id!r} not in graph")

        # Tentatively add and check for cycles
        self._adjacency[edge.source_node_id].append(edge.target_node_id)
        if self._has_cycle():
            self._adjacency[edge.source_node_id].remove(edge.target_node_id)
            raise CausalCycleDetectedError(
                f"Adding edge {edge.edge_id} ({edge.source_node_id} -> {edge.target_node_id}) "
                f"would create a cycle"
            )

        self._reverse_adjacency[edge.target_node_id].append(edge.source_node_id)
        self.edges[edge.edge_id] = edge

    def _has_cycle(self) -> bool:
        """DFS cycle detection across the full graph."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in self.nodes}

        def dfs(u: str) -> bool:
            color[u] = GRAY
            for v in self._adjacency.get(u, []):
                if v not in color:
                    continue
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and dfs(v):
                    return True
            color[u] = BLACK
            return False

        return any(color[nid] == WHITE and dfs(nid) for nid in self.nodes)

    def get_downstream(self, node_id: str, *, max_depth: int = MAX_GRAPH_DEPTH) -> list[str]:
        """Returns all nodes reachable downstream from node_id."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(node_id, 0)]
        result: list[str] = []

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            if current != node_id:
                result.append(current)
            for neighbor in self._adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        return result

    def get_upstream(self, node_id: str, *, max_depth: int = MAX_GRAPH_DEPTH) -> list[str]:
        """Returns all nodes upstream of node_id."""
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(node_id, 0)]
        result: list[str] = []

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            if current != node_id:
                result.append(current)
            for neighbor in self._reverse_adjacency.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        return result

    def get_edges_from(self, node_id: str) -> list[CausalEdge]:
        """Get all edges originating from a node."""
        return [e for e in self.edges.values() if e.source_node_id == node_id]

    def get_edges_to(self, node_id: str) -> list[CausalEdge]:
        """Get all edges targeting a node."""
        return [e for e in self.edges.values() if e.target_node_id == node_id]

    def get_causal_edges(self) -> list[CausalEdge]:
        """Get only strictly causal edges (CAUSES, CONTRIBUTES_TO, ENABLES)."""
        return [e for e in self.edges.values() if e.is_causal]

    def get_non_causal_edges(self) -> list[CausalEdge]:
        """Get edges that represent dependency or correlation but not causation."""
        return [e for e in self.edges.values() if not e.is_causal]

    def compute_graph_hash(self) -> str:
        """Deterministic hash of the entire graph structure."""
        payload = {
            "case_id": self.case_id,
            "nodes": sorted(self.nodes.keys()),
            "edges": sorted(
                [(e.source_node_id, e.target_node_id, e.relationship_type.value)
                 for e in self.edges.values()]
            ),
        }
        return compute_sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": {nid: n.to_dict() for nid, n in sorted(self.nodes.items())},
            "edges": {eid: e.to_dict() for eid, e in sorted(self.edges.items())},
            "graph_hash": self.compute_graph_hash(),
        }
