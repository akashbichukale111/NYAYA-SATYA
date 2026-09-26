"""Dependency propagation engine for NYAYA-SATYA causal graph.

Propagates effects through the causal/dependency graph when a node's
state changes. Used by the blast-radius engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.causal_edge import CausalEdge, CausalRelationshipType
from nyaya_causal.contracts.effect import CausalEffect, EffectType
from nyaya_causal.graph.causal_graph import CausalGraph, MAX_GRAPH_DEPTH


@dataclass
class PropagationResult:
    """Result of propagating an intervention through the graph."""

    origin_node_id: str
    direct_effects: list[CausalEffect] = field(default_factory=list)
    indirect_effects: list[CausalEffect] = field(default_factory=list)
    unaffected_nodes: list[str] = field(default_factory=list)
    propagation_depth: int = 0
    bounded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_node_id": self.origin_node_id,
            "direct_effects": [e.to_dict() for e in self.direct_effects],
            "indirect_effects": [e.to_dict() for e in self.indirect_effects],
            "unaffected_nodes": self.unaffected_nodes,
            "propagation_depth": self.propagation_depth,
            "bounded": self.bounded,
        }


class DependencyPropagator:
    """Propagates effects through the causal graph from an intervention point."""

    # Edge types that propagate effects downstream
    PROPAGATING_TYPES = frozenset({
        CausalRelationshipType.CAUSES,
        CausalRelationshipType.CONTRIBUTES_TO,
        CausalRelationshipType.DEPENDS_ON,
        CausalRelationshipType.PRECONDITION_FOR,
        CausalRelationshipType.ENABLES,
    })

    def __init__(self, graph: CausalGraph, *, max_depth: int = MAX_GRAPH_DEPTH) -> None:
        self.graph = graph
        self.max_depth = max_depth

    def propagate(self, origin_id: str) -> PropagationResult:
        """Propagate effects from origin_id through the graph."""
        result = PropagationResult(origin_node_id=origin_id)

        if origin_id not in self.graph.nodes:
            return result

        visited: set[str] = {origin_id}
        queue: list[tuple[str, int, list[str]]] = [(origin_id, 0, [origin_id])]

        while queue:
            current, depth, path = queue.pop(0)

            if depth > self.max_depth:
                result.bounded = True
                continue

            # Find downstream edges
            for edge in self.graph.get_edges_from(current):
                if edge.relationship_type not in self.PROPAGATING_TYPES:
                    continue
                target = edge.target_node_id
                if target in visited:
                    continue

                visited.add(target)
                new_path = path + [target]

                effect = CausalEffect(
                    node_id=target,
                    node_type=self.graph.nodes[target].node_type.value if target in self.graph.nodes else "UNKNOWN",
                    effect_type=EffectType.DIRECT_EFFECT if depth == 0 else EffectType.INDIRECT_EFFECT,
                    description=f"Affected via {edge.relationship_type.value} from {current}",
                    path_from_intervention=new_path,
                    depth=depth + 1,
                )

                if depth == 0:
                    result.direct_effects.append(effect)
                else:
                    result.indirect_effects.append(effect)

                result.propagation_depth = max(result.propagation_depth, depth + 1)
                queue.append((target, depth + 1, new_path))

        # Identify unaffected nodes
        for nid in self.graph.nodes:
            if nid not in visited:
                result.unaffected_nodes.append(nid)

        return result
