"""
Simulation Runner: orchestrates one full simulation run.

    Base Snapshot -> clone -> apply mutations -> propagate failure(s)
    -> blast radius -> failure tree -> diff -> recovery options -> result

Non-destructive by construction: `base` and `simulated` are two separate
SimGraph instances; `base` is never mutated.
"""

from app.graph.graph_model import SimGraph
from app.graph.traversal import propagate_failure, compute_blast_radius, compute_criticality, build_failure_tree
from app.simulation_engine.mutation_engine import apply_mutations, MutationError
from app.simulation_engine.diff_engine import compute_diff
from app.simulation_engine.recovery_engine import generate_recovery_options


def run_simulation(base_snapshot_data: dict, mutations: list[dict]) -> dict:
    """
    mutations: list of {"mutation_type": str, "target_node_id": str}

    Returns a fully self-contained result dict (JSON-serializable) suitable
    for storing directly on Simulation.result.
    """
    base = SimGraph.from_snapshot_data(base_snapshot_data)
    simulated = base.clone()

    try:
        mutation_records = apply_mutations(simulated, mutations)
    except MutationError as e:
        return {
            "status": "FAILED",
            "error": str(e),
            "mutations_requested": mutations,
        }

    # Propagate from every mutated node and merge results.
    all_affected: dict[str, dict] = {}
    all_chains = []
    for record in mutation_records:
        prop = propagate_failure(simulated, record["target_node_id"])
        all_chains.extend(prop.cascade_chains)
        for a in prop.affected:
            existing = all_affected.get(a.node_id)
            if existing is None:
                all_affected[a.node_id] = {
                    "node_id": a.node_id, "node_type": a.node_type, "label": a.label,
                    "order": a.order, "impact_types": list(a.impact_types),
                    "new_status": a.new_status, "path_from_root": a.path_from_root,
                }
            else:
                # merge impact types from multiple mutation roots hitting the same node
                for it in a.impact_types:
                    if it not in existing["impact_types"]:
                        existing["impact_types"].append(it)

    affected_list = list(all_affected.values())

    # Blast radius aggregation (recompute directly from affected_list so multi-mutation merges correctly)
    blast_radius = _aggregate_blast_radius(mutation_records, affected_list)
    criticality = compute_criticality(base)  # criticality is a property of the BASE structure
    diff = compute_diff(base, simulated)
    recovery_options = generate_recovery_options(affected_list, blast_radius)

    human_review_required = len(blast_radius["human_review_items"]) > 0

    failure_trees = []
    for record in mutation_records:
        prop = propagate_failure(base.clone(), record["target_node_id"])
        failure_trees.append(build_failure_tree(base, prop))

    return {
        "status": "COMPLETED",
        "mutations_applied": mutation_records,
        "affected_nodes": affected_list,
        "cascade_chains": all_chains,
        "blast_radius": blast_radius,
        "criticality": {nid: criticality.get(nid) for nid in
                        {m["target_node_id"] for m in mutation_records} | {a["node_id"] for a in affected_list}},
        "failure_trees": failure_trees,
        "diff": diff,
        "recovery_options": recovery_options,
        "human_review_required": human_review_required,
        "simulated_state": simulated.to_dict(),
    }


def _aggregate_blast_radius(mutation_records: list[dict], affected_list: list[dict]) -> dict:
    by_type: dict[str, list[str]] = {}
    new_unknowns, new_conflicts, new_blocks, verification_gaps, human_review_items = [], [], [], [], []
    from app.enums import ImpactType, NodeStatus

    for a in affected_list:
        by_type.setdefault(a["node_type"], []).append(a["node_id"])
        if ImpactType.NEW_UNKNOWN.value in a["impact_types"]:
            new_unknowns.append(a["node_id"])
        if ImpactType.NEW_CONFLICT.value in a["impact_types"]:
            new_conflicts.append(a["node_id"])
        if ImpactType.NEWLY_BLOCKED.value in a["impact_types"]:
            new_blocks.append(a["node_id"])
        if ImpactType.VERIFICATION_GAP.value in a["impact_types"]:
            verification_gaps.append(a["node_id"])
        if a["new_status"] == NodeStatus.REQUIRES_HUMAN_REVIEW.value:
            human_review_items.append(a["node_id"])

    return {
        "root_node_ids": [m["target_node_id"] for m in mutation_records],
        "directly_affected_nodes": [a["node_id"] for a in affected_list if a["order"] == 2],
        "indirectly_affected_nodes": [a["node_id"] for a in affected_list if a["order"] > 2],
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
        "total_affected_count": len(affected_list),
    }
