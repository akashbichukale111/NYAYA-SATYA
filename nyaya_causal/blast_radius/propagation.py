"""Effect propagation utilities for blast-radius calculations.

Propagates structural effects through claim dependency chains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nyaya_causal.contracts.effect import CausalEffect, EffectType


@dataclass
class EffectChain:
    """A chain of propagated effects from an origin."""

    origin_id: str
    chain: list[CausalEffect] = field(default_factory=list)
    max_depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "chain": [e.to_dict() for e in self.chain],
            "max_depth": self.max_depth,
        }


class EffectPropagator:
    """Propagates effects through case dependency relationships."""

    def __init__(self, *, max_depth: int = 50) -> None:
        self.max_depth = max_depth

    def propagate_through_dependencies(
        self,
        origin_id: str,
        dependency_map: dict[str, list[str]],
        affected_nodes: set[str],
    ) -> EffectChain:
        """Propagate effects from origin through dependency edges."""
        chain = EffectChain(origin_id=origin_id)
        visited: set[str] = {origin_id}
        queue: list[tuple[str, int]] = [(origin_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth > self.max_depth:
                break

            for dependent in dependency_map.get(current, []):
                if dependent not in visited:
                    visited.add(dependent)
                    affected_nodes.add(dependent)
                    effect = CausalEffect(
                        node_id=dependent,
                        node_type="CLAIM",
                        effect_type=EffectType.INDIRECT_EFFECT,
                        description=f"Propagated effect from {origin_id} via dependency chain",
                        path_from_intervention=[origin_id, dependent],
                        depth=depth + 1,
                    )
                    chain.chain.append(effect)
                    chain.max_depth = max(chain.max_depth, depth + 1)
                    queue.append((dependent, depth + 1))

        return chain
