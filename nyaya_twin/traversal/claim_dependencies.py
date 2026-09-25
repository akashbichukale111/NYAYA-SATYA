"""Claim dependency traversals for NYAYA-SATYA Case Digital Twin.

Answers:
1. What prerequisite claims must be established before claim C?
2. What downstream claims depend on claim C?
"""

from __future__ import annotations

from collections import deque

from nyaya_twin.contracts.case_twin import CaseDigitalTwin
from nyaya_twin.contracts.relationships import RelationshipType


def get_claim_prerequisites(twin: CaseDigitalTwin, claim_id: str) -> list[str]:
    """Returns direct prerequisite claims that claim_id depends on."""
    prereqs = set()
    for rel in twin.relationships.values():
        if (
            rel.source_id == claim_id
            and rel.relationship_type is RelationshipType.DEPENDS_ON
            and rel.target_type == "CLAIM"
        ):
            prereqs.add(rel.target_id)
    return sorted(prereqs)


def get_claim_dependents(twin: CaseDigitalTwin, claim_id: str) -> list[str]:
    """Returns direct dependent claims that depend on claim_id."""
    deps = set()
    for rel in twin.relationships.values():
        if (
            rel.target_id == claim_id
            and rel.relationship_type is RelationshipType.DEPENDS_ON
            and rel.source_type == "CLAIM"
        ):
            deps.add(rel.source_id)
    return sorted(deps)


def get_claim_ancestors(twin: CaseDigitalTwin, claim_id: str) -> list[str]:
    """Returns all transitive upstream prerequisites for claim_id."""
    visited: set[str] = set()
    queue = deque(get_claim_prerequisites(twin, claim_id))
    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)
        for p in get_claim_prerequisites(twin, curr):
            if p not in visited:
                queue.append(p)
    return sorted(visited)


def get_claim_descendants(twin: CaseDigitalTwin, claim_id: str) -> list[str]:
    """Returns all transitive downstream dependents for claim_id."""
    visited: set[str] = set()
    queue = deque(get_claim_dependents(twin, claim_id))
    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue
        visited.add(curr)
        for d in get_claim_dependents(twin, curr):
            if d not in visited:
                queue.append(d)
    return sorted(visited)
