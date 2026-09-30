"""
Failure Propagation + Blast Radius + Criticality engine.

Pure, deterministic graph algorithms. No LLM calls here — per spec,
"Prefer deterministic graph/rule algorithms for simulation correctness.
LLMs may assist scenario explanation, but must not be the authority for
graph state calculation."

Everything here answers structural questions only:
  WHAT DEPENDS ON IT? WHAT IS AFFECTED? WHAT NEW GAP APPEARS?
It never labels anything a legal outcome.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque

from app.graph.graph_model import SimGraph
from app.enums import NodeStatus, ImpactType, CriticalityLabel


@dataclass
class AffectedNode:
    node_id: str
    node_type: str
    label: str
    order: int  # 1 = directly affected, 2 = first-order dependency, 3+ = further downstream
    impact_types: list[str] = field(default_factory=list)
    new_status: str | None = None
    path_from_root: list[str] = field(default_factory=list)  # cascade chain of node ids


@dataclass
class PropagationResult:
    root_node_id: str
    affected: list[AffectedNode]  # ordered by BFS order, root excluded
    cascade_chains: list[list[str]]  # each chain: [root, ..., leaf] of ids that got affected


def propagate_failure(graph: SimGraph, root_node_id: str, max_depth: int = 12) -> PropagationResult:
    """
    BFS outward from root_node_id along "depends on me" edges, marking each
    reached node with a derived impact_type based on its own edge type to the
    node that affected it. Mutates graph node statuses in place (this is the
    SIMULATED graph clone — never the production graph).
    """
    visited = {root_node_id}
    queue = deque([(root_node_id, 1, [root_node_id])])
    affected: list[AffectedNode] = []
    chains: list[list[str]] = []

    while queue:
        current_id, order, path = queue.popleft()
        if order > max_depth:
            continue
        dependents = graph.neighbors_dependent_on(current_id)
        if not dependents and len(path) > 1:
            chains.append(path)
        for dep_id in dependents:
            if dep_id in visited:
                continue
            visited.add(dep_id)
            node = graph.nodes.get(dep_id)
            if node is None:
                continue
            impact_types, new_status = _derive_impact(graph, current_id, dep_id, node)
            node.status = new_status
            affected.append(AffectedNode(
                node_id=dep_id,
                node_type=node.node_type,
                label=node.label,
                order=order + 1,
                impact_types=impact_types,
                new_status=new_status,
                path_from_root=path + [dep_id],
            ))
            queue.append((dep_id, order + 1, path + [dep_id]))

    return PropagationResult(root_node_id=root_node_id, affected=affected, cascade_chains=chains)


def _derive_impact(graph: SimGraph, source_id: str, target_id: str, target_node) -> tuple[list[str], str]:
    """
    Decide the impact label(s) + resulting status for `target_node`, given
    that `source_id` (its dependency) changed. Rule-based, deterministic.
    """
    source = graph.nodes.get(source_id)
    source_status = source.status if source else NodeStatus.UNKNOWN.value

    impacts: list[str] = []
    new_status = target_node.status

    if source_status in (NodeStatus.EXCLUDED.value, NodeStatus.MISSING.value):
        impacts.append(ImpactType.SUPPORT_GAP.value)
        new_status = NodeStatus.REQUIRES_HUMAN_REVIEW.value
    elif source_status == NodeStatus.UNVERIFIED.value:
        impacts.append(ImpactType.VERIFICATION_GAP.value)
        new_status = NodeStatus.UNVERIFIED.value
    elif source_status == NodeStatus.CONFLICTING.value:
        impacts.append(ImpactType.NEW_CONFLICT.value)
        new_status = NodeStatus.CONFLICTING.value
    elif source_status == NodeStatus.UNKNOWN.value:
        impacts.append(ImpactType.NEW_UNKNOWN.value)
        new_status = NodeStatus.UNKNOWN.value
    elif source_status == NodeStatus.BLOCKED.value:
        impacts.append(ImpactType.NEWLY_BLOCKED.value)
        new_status = NodeStatus.BLOCKED.value
    elif source_status == NodeStatus.SUPERSEDED.value:
        impacts.append(ImpactType.VERIFICATION_GAP.value)
        new_status = NodeStatus.REQUIRES_HUMAN_REVIEW.value
    else:
        impacts.append(ImpactType.REVIEW_REQUIRED.value)
        new_status = NodeStatus.REQUIRES_HUMAN_REVIEW.value

    # Node types that are inherently gating (deadlines, verifications, workflows/actions)
    # additionally flip to BLOCKED when their dependency is gone, since a missing
    # dependency structurally blocks them regardless of the source's own status label.
    if target_node.node_type in ("WORKFLOW", "ACTION", "OBLIGATION", "DEADLINE") and \
            source_status in (NodeStatus.EXCLUDED.value, NodeStatus.MISSING.value, NodeStatus.BLOCKED.value):
        new_status = NodeStatus.BLOCKED.value
        if ImpactType.NEWLY_BLOCKED.value not in impacts:
            impacts.append(ImpactType.NEWLY_BLOCKED.value)

    return impacts, new_status


def compute_blast_radius(graph: SimGraph, root_node_id: str, propagation: PropagationResult) -> dict:
    """Aggregate propagation results into the spec's blast-radius shape."""
    by_type: dict[str, list[str]] = {}
    new_unknowns, new_conflicts, new_blocks, verification_gaps, human_review_items = [], [], [], [], []

    for a in propagation.affected:
        by_type.setdefault(a.node_type, []).append(a.node_id)
        if ImpactType.NEW_UNKNOWN.value in a.impact_types:
            new_unknowns.append(a.node_id)
        if ImpactType.NEW_CONFLICT.value in a.impact_types:
            new_conflicts.append(a.node_id)
        if ImpactType.NEWLY_BLOCKED.value in a.impact_types:
            new_blocks.append(a.node_id)
        if ImpactType.VERIFICATION_GAP.value in a.impact_types:
            verification_gaps.append(a.node_id)
        if a.new_status == NodeStatus.REQUIRES_HUMAN_REVIEW.value:
            human_review_items.append(a.node_id)

    return {
        "root_node_id": root_node_id,
        "directly_affected_nodes": [a.node_id for a in propagation.affected if a.order == 2],
        "indirectly_affected_nodes": [a.node_id for a in propagation.affected if a.order > 2],
        "affected_documents": by_type.get("DOCUMENT", []),
        "affected_evidence": by_type.get("EVIDENCE", []),
        "affected_claims": by_type.get("CLAIM", []),
        "affected_issues": by_type.get("ISSUE", []),
        "affected_obligations": by_type.get("OBLIGATION", []),
        "affected_deadlines": by_type.get("DEADLINE", []),
        "affected_hearings": by_type.get("HEARING", []),
        "affected_registry_defects": by_type.get("REGISTRY_DEFECT", []),
        "affected_workflows": by_type.get("WORKFLOW", []) + by_type.get("ACTION", []),
        "new_unknowns": new_unknowns,
        "new_conflicts": new_conflicts,
        "new_blocks": new_blocks,
        "verification_gaps": verification_gaps,
        "human_review_items": human_review_items,
        "total_affected_count": len(propagation.affected),
    }


def compute_criticality(graph: SimGraph) -> dict[str, str]:
    """
    Structural criticality per node, based purely on in-degree of
    dependency-carrying edges (how many other nodes rely on this one).
    Labels are graph-structure descriptions ONLY — see enums.CriticalityLabel docstring.
    """
    dependency_counts: dict[str, int] = {n_id: 0 for n_id in graph.nodes}
    for node_id in graph.nodes:
        for dep_id in graph.neighbors_dependent_on(node_id):
            dependency_counts[node_id] = dependency_counts.get(node_id, 0) + 1

    labels: dict[str, str] = {}
    for node_id, count in dependency_counts.items():
        if count == 0:
            labels[node_id] = CriticalityLabel.ISOLATED.value
        elif count == 1:
            labels[node_id] = CriticalityLabel.LOW_DEPENDENCY.value
        elif count <= 3:
            labels[node_id] = CriticalityLabel.MULTI_DEPENDENCY.value
        else:
            labels[node_id] = CriticalityLabel.HIGH_DEPENDENCY.value

    # SINGLE_POINT_DEPENDENCY: this node is the ONLY dependency-source for at
    # least one downstream node (i.e. removing it leaves that node with zero
    # remaining support from any other node of the same relationship shape).
    for node_id in graph.nodes:
        dependents = graph.neighbors_dependent_on(node_id)
        for dep_id in dependents:
            # does dep_id (the dependent) have any OTHER node it depends on besides node_id?
            other_sources = [s for s in graph.dependency_sources(dep_id) if s != node_id]
            if not other_sources and dependency_counts.get(node_id, 0) >= 1:
                labels[node_id] = CriticalityLabel.SINGLE_POINT_DEPENDENCY.value

    return labels


def build_failure_tree(graph: SimGraph, propagation: PropagationResult) -> dict:
    """
    Root Failure -> Direct Impact / Dependency Impact / Verification Impact /
    Workflow Impact / Human Review, each linking to actual affected node ids.
    """
    direct = [a for a in propagation.affected if a.order == 2]
    dependency = [a for a in propagation.affected if a.order > 2]
    verification = [a for a in propagation.affected if ImpactType.VERIFICATION_GAP.value in a.impact_types]
    workflow = [a for a in propagation.affected if a.node_type in ("WORKFLOW", "ACTION")]
    human_review = [a for a in propagation.affected if a.new_status == NodeStatus.REQUIRES_HUMAN_REVIEW.value]

    def _leaf(a: AffectedNode) -> dict:
        return {
            "node_id": a.node_id, "node_type": a.node_type, "label": a.label,
            "impact_types": a.impact_types, "new_status": a.new_status,
            "path_from_root": a.path_from_root,
        }

    return {
        "root_failure": propagation.root_node_id,
        "direct_impact": [_leaf(a) for a in direct],
        "dependency_impact": [_leaf(a) for a in dependency],
        "verification_impact": [_leaf(a) for a in verification],
        "workflow_impact": [_leaf(a) for a in workflow],
        "human_review": [_leaf(a) for a in human_review],
        "cascade_chains": propagation.cascade_chains,
    }
