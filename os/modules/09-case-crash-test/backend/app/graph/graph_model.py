"""
A lightweight, pure-Python in-memory graph used exclusively for simulation.
This is deliberately NOT the SQLAlchemy models: simulations must never touch
the production ORM session in a way that could be committed. We load a
snapshot's serialized JSON into this structure, mutate freely, and discard it.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import copy


@dataclass
class GNode:
    id: str
    node_type: str
    label: str
    status: str
    attributes: dict = field(default_factory=dict)
    provenance_ref: Optional[str] = None


@dataclass
class GEdge:
    id: str
    source_id: str
    target_id: str
    rel_type: str
    attributes: dict = field(default_factory=dict)


class SimGraph:
    """An isolated, mutable in-memory clone of a case graph."""

    def __init__(self, nodes: list[GNode], edges: list[GEdge]):
        self.nodes: dict[str, GNode] = {n.id: n for n in nodes}
        self.edges: list[GEdge] = edges
        self._out: dict[str, list[GEdge]] = {}
        self._in: dict[str, list[GEdge]] = {}
        for e in edges:
            self._out.setdefault(e.source_id, []).append(e)
            self._in.setdefault(e.target_id, []).append(e)

    @classmethod
    def from_snapshot_data(cls, data: dict) -> "SimGraph":
        nodes = [GNode(**n) for n in data.get("nodes", [])]
        edges = [GEdge(**e) for e in data.get("relationships", [])]
        return cls(nodes, edges)

    def clone(self) -> "SimGraph":
        return copy.deepcopy(self)

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {
                    "id": n.id, "node_type": n.node_type, "label": n.label,
                    "status": n.status, "attributes": n.attributes,
                    "provenance_ref": n.provenance_ref,
                }
                for n in self.nodes.values()
            ],
            "relationships": [
                {
                    "id": e.id, "source_id": e.source_id, "target_id": e.target_id,
                    "rel_type": e.rel_type, "attributes": e.attributes,
                }
                for e in self.edges
            ],
        }

    def out_edges(self, node_id: str) -> list[GEdge]:
        return self._out.get(node_id, [])

    def in_edges(self, node_id: str) -> list[GEdge]:
        return self._in.get(node_id, [])

    def neighbors_dependent_on(self, node_id: str) -> list[str]:
        """
        Nodes that DEPEND on `node_id` in a propagation-relevant way, i.e.
        nodes that would be affected if `node_id` changes state:
          - X --DEPENDS_ON--> node_id   => X depends on node_id
          - X --REQUIRES--> node_id     => X depends on node_id
          - X --VERIFIED_BY--> node_id  => X depends on node_id
          - node_id --SUPPORTS--> X     => X depends on node_id (support flows forward)
          - node_id --TRIGGERS--> X     => X depends on node_id
          - node_id --BLOCKS--> X       => X depends on node_id
        """
        dependents = set()
        for e in self._in.get(node_id, []):
            if e.rel_type in ("DEPENDS_ON", "REQUIRES", "VERIFIED_BY"):
                dependents.add(e.source_id)
        for e in self._out.get(node_id, []):
            if e.rel_type in ("SUPPORTS", "TRIGGERS", "BLOCKS"):
                dependents.add(e.target_id)
        return list(dependents)

    def dependency_sources(self, node_id: str) -> list[str]:
        """
        Inverse of neighbors_dependent_on: the nodes that `node_id` itself
        depends on (i.e. nodes that, if disturbed, would affect `node_id`).
          - node_id --DEPENDS_ON/REQUIRES/VERIFIED_BY--> X  => node_id depends on X
          - X --SUPPORTS/TRIGGERS/BLOCKS--> node_id         => node_id depends on X
        """
        sources = set()
        for e in self._out.get(node_id, []):
            if e.rel_type in ("DEPENDS_ON", "REQUIRES", "VERIFIED_BY"):
                sources.add(e.target_id)
        for e in self._in.get(node_id, []):
            if e.rel_type in ("SUPPORTS", "TRIGGERS", "BLOCKS"):
                sources.add(e.source_id)
        return list(sources)
