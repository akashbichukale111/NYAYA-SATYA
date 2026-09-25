"""Directed Acyclic Dependency Graph for NYAYA-SATYA Case Digital Twin.

Enforces cycle detection, ancestor/descendant resolution, and deterministic topological ordering.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class DependencyCycleError(ValueError):
    """Raised when a dependency cycle is introduced where semantics forbid cycles."""


class DependencyGraph:
    """Deterministic directed dependency graph with cycle detection."""

    def __init__(self) -> None:
        # source -> set of targets (source depends on target)
        self._dependencies: dict[str, set[str]] = defaultdict(set)
        # target -> set of sources (target is depended on by source)
        self._reverse_dependencies: dict[str, set[str]] = defaultdict(set)
        self._nodes: set[str] = set()

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes)

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)

    def add_dependency(self, source_id: str, depends_on_id: str) -> None:
        """Adds a dependency: source_id DEPENDS_ON depends_on_id.

        Raises DependencyCycleError if this creates a cycle.
        """
        if source_id == depends_on_id:
            raise DependencyCycleError(f"Self-dependency prohibited: node {source_id} cannot depend on itself")

        # Check if adding this edge would create a cycle (i.e. depends_on_id already transitively depends on source_id)
        if self.has_transitive_path(depends_on_id, source_id):
            raise DependencyCycleError(
                f"Dependency cycle detected: adding edge {source_id} -> {depends_on_id} forms a closed cycle"
            )

        self._nodes.add(source_id)
        self._nodes.add(depends_on_id)
        self._dependencies[source_id].add(depends_on_id)
        self._reverse_dependencies[depends_on_id].add(source_id)

    def has_transitive_path(self, start_id: str, target_id: str) -> bool:
        """Returns True if there is a path from start_id to target_id."""
        if start_id == target_id:
            return True
        visited = set()
        queue = deque([start_id])
        while queue:
            curr = queue.popleft()
            if curr == target_id:
                return True
            if curr in visited:
                continue
            visited.add(curr)
            for neighbor in sorted(self._dependencies.get(curr, set())):
                if neighbor not in visited:
                    queue.append(neighbor)
        return False

    def get_prerequisites(self, node_id: str) -> list[str]:
        """Returns direct prerequisites that node_id depends on (sorted)."""
        return sorted(self._dependencies.get(node_id, set()))

    def get_dependents(self, node_id: str) -> list[str]:
        """Returns direct dependents that depend on node_id (sorted)."""
        return sorted(self._reverse_dependencies.get(node_id, set()))

    def get_ancestors(self, node_id: str) -> list[str]:
        """Returns all transitive prerequisites of node_id in deterministic order."""
        visited: set[str] = set()
        queue = deque(sorted(self._dependencies.get(node_id, set())))
        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            for prereq in sorted(self._dependencies.get(curr, set())):
                if prereq not in visited:
                    queue.append(prereq)
        return sorted(visited)

    def get_descendants(self, node_id: str) -> list[str]:
        """Returns all downstream transitive dependents of node_id in deterministic order."""
        visited: set[str] = set()
        queue = deque(sorted(self._reverse_dependencies.get(node_id, set())))
        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            for dep in sorted(self._reverse_dependencies.get(curr, set())):
                if dep not in visited:
                    queue.append(dep)
        return sorted(visited)

    def topological_sort(self) -> list[str]:
        """Returns a deterministic topological sort of all nodes."""
        in_degree: dict[str, int] = {node: 0 for node in self._nodes}
        for node in self._nodes:
            for prereq in self._dependencies.get(node, set()):
                # prereq comes before node, so node has in-degree from prereq
                in_degree[node] += 1

        # Queue nodes with in_degree 0
        queue = deque(sorted([node for node, deg in in_degree.items() if deg == 0]))
        result: list[str] = []

        while queue:
            curr = queue.popleft()
            result.append(curr)
            # Find nodes that depend on curr
            for dependent in sorted(self._reverse_dependencies.get(curr, set())):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._nodes):
            raise DependencyCycleError("Dependency cycle exists in graph; cannot complete topological sort")

        return result
