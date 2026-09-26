"""Causal path analysis engine for NYAYA-SATYA.

Deterministic path traversal between nodes in the causal graph.
Bounded depth prevents infinite search. Returns paths with intermediate
nodes, supporting evidence, assumptions, and unresolved links.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.causal_edge import CausalEdge, CausalEdgeStatus
from nyaya_causal.graph.causal_graph import CausalGraph, MAX_GRAPH_DEPTH, MAX_PATHS
from tarka_vyuh.contracts.provenance import compute_sha256


@dataclass
class CausalPath:
    """A single causal path from source to target."""

    path_nodes: list[str]
    path_edges: list[str]
    supporting_evidence_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unresolved_links: list[str] = field(default_factory=list)
    depth: int = 0
    is_bounded: bool = False

    @property
    def path_hash(self) -> str:
        return compute_sha256({"nodes": self.path_nodes, "edges": self.path_edges})

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_nodes": self.path_nodes,
            "path_edges": self.path_edges,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "assumptions": self.assumptions,
            "unresolved_links": self.unresolved_links,
            "depth": self.depth,
            "is_bounded": self.is_bounded,
            "path_hash": self.path_hash,
        }


@dataclass
class PathAnalysisResult:
    """Result of a path analysis query."""

    source_id: str
    target_id: str
    paths_found: list[CausalPath] = field(default_factory=list)
    alternative_paths: list[CausalPath] = field(default_factory=list)
    analysis_bounded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "paths_found": [p.to_dict() for p in self.paths_found],
            "alternative_paths": [p.to_dict() for p in self.alternative_paths],
            "analysis_bounded": self.analysis_bounded,
            "total_paths": len(self.paths_found) + len(self.alternative_paths),
        }


class PathEngine:
    """Deterministic path traversal engine."""

    def __init__(self, graph: CausalGraph, *, max_depth: int = MAX_GRAPH_DEPTH, max_paths: int = MAX_PATHS) -> None:
        self.graph = graph
        self.max_depth = max_depth
        self.max_paths = max_paths

    def find_paths(self, source_id: str, target_id: str) -> PathAnalysisResult:
        """Find all paths from source to target, bounded by depth and count."""
        if source_id not in self.graph.nodes:
            raise ValueError(f"Source node {source_id!r} not in graph")
        if target_id not in self.graph.nodes:
            raise ValueError(f"Target node {target_id!r} not in graph")

        result = PathAnalysisResult(source_id=source_id, target_id=target_id)
        raw_paths: list[list[str]] = []
        self._dfs_paths(source_id, target_id, [source_id], set(), raw_paths)

        if len(raw_paths) > self.max_paths:
            result.analysis_bounded = True
            raw_paths = raw_paths[:self.max_paths]

        for node_path in raw_paths:
            causal_path = self._build_causal_path(node_path)
            result.paths_found.append(causal_path)

        return result

    def find_alternative_causes(self, target_id: str) -> list[CausalPath]:
        """Detect multiple possible causes for target_id."""
        incoming_edges = self.graph.get_edges_to(target_id)
        paths: list[CausalPath] = []
        for edge in incoming_edges:
            if edge.is_causal:
                path = CausalPath(
                    path_nodes=[edge.source_node_id, target_id],
                    path_edges=[edge.edge_id],
                    supporting_evidence_ids=list(edge.supporting_evidence_ids),
                    assumptions=list(edge.assumptions),
                    depth=1,
                )
                if edge.status == CausalEdgeStatus.CAUSALITY_UNRESOLVED:
                    path.unresolved_links.append(edge.edge_id)
                paths.append(path)
        return paths

    def _dfs_paths(
        self,
        current: str,
        target: str,
        path: list[str],
        visited: set[str],
        results: list[list[str]],
    ) -> None:
        if len(results) >= self.max_paths:
            return
        if len(path) > self.max_depth:
            return
        if current == target and len(path) > 1:
            results.append(list(path))
            return

        visited.add(current)
        for neighbor in self.graph._adjacency.get(current, []):
            if neighbor not in visited:
                path.append(neighbor)
                self._dfs_paths(neighbor, target, path, visited, results)
                path.pop()
        visited.discard(current)

    def _build_causal_path(self, node_path: list[str]) -> CausalPath:
        edge_ids: list[str] = []
        evidence: list[str] = []
        assumptions: list[str] = []
        unresolved: list[str] = []

        for i in range(len(node_path) - 1):
            src, tgt = node_path[i], node_path[i + 1]
            for edge in self.graph.edges.values():
                if edge.source_node_id == src and edge.target_node_id == tgt:
                    edge_ids.append(edge.edge_id)
                    evidence.extend(edge.supporting_evidence_ids)
                    assumptions.extend(edge.assumptions)
                    if edge.status == CausalEdgeStatus.CAUSALITY_UNRESOLVED:
                        unresolved.append(edge.edge_id)
                    break

        return CausalPath(
            path_nodes=node_path,
            path_edges=edge_ids,
            supporting_evidence_ids=list(dict.fromkeys(evidence)),
            assumptions=list(dict.fromkeys(assumptions)),
            unresolved_links=unresolved,
            depth=len(node_path) - 1,
            is_bounded=len(node_path) - 1 >= self.max_depth,
        )
