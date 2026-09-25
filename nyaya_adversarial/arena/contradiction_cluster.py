"""Contradiction clustering for Evidence Conflict Arena.

Groups interconnected evidentiary conflicts by common entities, evidence nodes,
claims, or subject matter to expose systemic contradiction networks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from nyaya_adversarial.contracts.conflict import ConflictSet, EvidenceConflict


@dataclass
class ConflictCluster:
    """A cluster of interrelated evidentiary conflicts."""

    cluster_id: str
    case_id: str
    conflicts: list[EvidenceConflict]
    evidence_ids: list[str]
    claim_ids: list[str]
    primary_subject: str
    total_conflicts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.total_conflicts = len(self.conflicts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "case_id": self.case_id,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "evidence_ids": self.evidence_ids,
            "claim_ids": self.claim_ids,
            "primary_subject": self.primary_subject,
            "total_conflicts": len(self.conflicts),
            "created_at": self.created_at.isoformat(),
        }


class ContradictionClusterer:
    """Disjoint-set graph clusterer for evidentiary conflicts."""

    def cluster_conflicts(self, conflict_set: ConflictSet) -> list[ConflictCluster]:
        """Clusters conflicts sharing any evidence ID or claim ID."""
        if not conflict_set.conflicts:
            return []

        # Graph adjacency over conflicts
        adj: dict[int, set[int]] = {i: set() for i in range(len(conflict_set.conflicts))}
        for i in range(len(conflict_set.conflicts)):
            c1 = conflict_set.conflicts[i]
            evs_1 = {c1.evidence_a_id, c1.evidence_b_id}
            cls_1 = set(c1.claim_ids)
            for j in range(i + 1, len(conflict_set.conflicts)):
                c2 = conflict_set.conflicts[j]
                evs_2 = {c2.evidence_a_id, c2.evidence_b_id}
                cls_2 = set(c2.claim_ids)
                # Overlap in evidence or claim IDs indicates a common conflict network
                if (evs_1 & evs_2) or (cls_1 and cls_2 and (cls_1 & cls_2)):
                    adj[i].add(j)
                    adj[j].add(i)

        # Connected components via BFS
        visited: set[int] = set()
        clusters: list[ConflictCluster] = []
        cluster_idx = 1

        for i in range(len(conflict_set.conflicts)):
            if i in visited:
                continue

            comp: list[int] = []
            queue = [i]
            visited.add(i)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            comp_conflicts = [conflict_set.conflicts[k] for k in comp]
            ev_set: set[str] = set()
            cl_set: set[str] = set()
            for c in comp_conflicts:
                ev_set.add(c.evidence_a_id)
                ev_set.add(c.evidence_b_id)
                cl_set.update(c.claim_ids)

            primary_subject = comp_conflicts[0].subject if comp_conflicts else "General Evidence Conflict"

            clusters.append(
                ConflictCluster(
                    cluster_id=f"cluster_{cluster_idx}",
                    case_id=conflict_set.case_id,
                    conflicts=comp_conflicts,
                    evidence_ids=sorted(ev_set),
                    claim_ids=sorted(cl_set),
                    primary_subject=primary_subject,
                )
            )
            cluster_idx += 1

        return clusters
