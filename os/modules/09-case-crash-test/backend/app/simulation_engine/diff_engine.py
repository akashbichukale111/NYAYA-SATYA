"""
State Diff engine: compares the base (real) snapshot graph to the simulated
graph and reports exactly what changed. Pure comparison, no interpretation.
"""

from app.graph.graph_model import SimGraph


def compute_diff(base: SimGraph, simulated: SimGraph) -> dict:
    changed_nodes = []
    for node_id, base_node in base.nodes.items():
        sim_node = simulated.nodes.get(node_id)
        if sim_node is None:
            changed_nodes.append({
                "node_id": node_id, "label": base_node.label,
                "change": "REMOVED_IN_SIMULATION",
                "base_status": base_node.status, "simulated_status": None,
            })
            continue
        if sim_node.status != base_node.status:
            changed_nodes.append({
                "node_id": node_id, "label": base_node.label, "node_type": base_node.node_type,
                "change": "STATUS_CHANGED",
                "base_status": base_node.status, "simulated_status": sim_node.status,
            })

    added_nodes = [
        {"node_id": n_id, "label": n.label, "change": "ADDED_IN_SIMULATION", "simulated_status": n.status}
        for n_id, n in simulated.nodes.items() if n_id not in base.nodes
    ]

    return {
        "changed_node_count": len(changed_nodes),
        "changed_nodes": changed_nodes,
        "added_nodes": added_nodes,
        "base_node_count": len(base.nodes),
        "simulated_node_count": len(simulated.nodes),
    }
