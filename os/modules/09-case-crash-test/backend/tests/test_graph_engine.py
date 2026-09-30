from app.graph.graph_model import SimGraph, GNode, GEdge
from app.graph.traversal import propagate_failure, compute_blast_radius, compute_criticality, build_failure_tree
from app.simulation_engine.mutation_engine import apply_mutation, apply_mutations, MutationError
from app.simulation_engine.diff_engine import compute_diff
from app.simulation_engine.recovery_engine import generate_recovery_options
from app.simulation_engine.runner import run_simulation
from app.enums import NodeStatus, ImpactType, CriticalityLabel, MutationType


def _chain_graph():
    """
    evidence <-DEPENDS_ON- claim <-DEPENDS_ON- issue <-DEPENDS_ON- obligation <-DEPENDS_ON- hearing
    i.e. claim DEPENDS_ON evidence, issue DEPENDS_ON claim, etc.
    """
    nodes = [
        GNode(id="evidence", node_type="EVIDENCE", label="Evidence E12", status="VERIFIED"),
        GNode(id="claim", node_type="CLAIM", label="Claim C4", status="VERIFIED"),
        GNode(id="issue", node_type="ISSUE", label="Issue I2", status="KNOWN"),
        GNode(id="obligation", node_type="OBLIGATION", label="Obligation O3", status="KNOWN"),
        GNode(id="hearing", node_type="HEARING", label="Hearing H1", status="KNOWN"),
    ]
    edges = [
        GEdge(id="e1", source_id="claim", target_id="evidence", rel_type="DEPENDS_ON"),
        GEdge(id="e2", source_id="issue", target_id="claim", rel_type="DEPENDS_ON"),
        GEdge(id="e3", source_id="obligation", target_id="issue", rel_type="DEPENDS_ON"),
        GEdge(id="e4", source_id="hearing", target_id="obligation", rel_type="DEPENDS_ON"),
    ]
    return SimGraph(nodes, edges)


def test_propagation_finds_all_downstream_nodes():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    affected_ids = {a.node_id for a in result.affected}
    assert affected_ids == {"claim", "issue", "obligation", "hearing"}


def test_propagation_order_increases_with_distance():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    order_by_id = {a.node_id: a.order for a in result.affected}
    assert order_by_id["claim"] < order_by_id["issue"] < order_by_id["obligation"] < order_by_id["hearing"]


def test_removed_evidence_creates_support_gap_impact():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    claim_node = next(a for a in result.affected if a.node_id == "claim")
    assert ImpactType.SUPPORT_GAP.value in claim_node.impact_types
    assert claim_node.new_status == NodeStatus.REQUIRES_HUMAN_REVIEW.value


def test_simulation_never_mutates_base_graph():
    graph = _chain_graph()
    original_statuses = {n.id: n.status for n in graph.nodes.values()}
    clone = graph.clone()
    apply_mutation(clone, MutationType.REMOVE_EVIDENCE.value, "evidence")
    propagate_failure(clone, "evidence")
    assert {n.id: n.status for n in graph.nodes.values()} == original_statuses


def test_blast_radius_shape_and_counts():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    br = compute_blast_radius(graph, "evidence", result)
    assert br["affected_claims"] == ["claim"]
    assert br["affected_issues"] == ["issue"]
    assert br["affected_obligations"] == ["obligation"]
    assert br["affected_hearings"] == ["hearing"]
    assert br["total_affected_count"] == 4
    assert set(br["human_review_items"]) == {"claim", "issue", "obligation", "hearing"}


def test_criticality_single_point_dependency():
    graph = _chain_graph()
    labels = compute_criticality(graph)
    # "evidence" is the sole dependency-source for "claim" -> single point of failure
    assert labels["evidence"] == CriticalityLabel.SINGLE_POINT_DEPENDENCY.value


def test_criticality_isolated_node_has_no_dependents():
    nodes = [GNode(id="lonely", node_type="DOCUMENT", label="Doc", status="KNOWN")]
    graph = SimGraph(nodes, [])
    labels = compute_criticality(graph)
    assert labels["lonely"] == CriticalityLabel.ISOLATED.value


def test_failure_tree_links_to_real_nodes():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    tree = build_failure_tree(graph, result)
    assert tree["root_failure"] == "evidence"
    direct_ids = {n["node_id"] for n in tree["direct_impact"]}
    assert direct_ids == {"claim"}
    all_ids = {n["node_id"] for n in tree["dependency_impact"]}
    assert all_ids == {"issue", "obligation", "hearing"}


def test_cascade_chain_captures_full_path():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    assert ["evidence", "claim", "issue", "obligation", "hearing"] in result.cascade_chains


def test_unknown_mutation_type_raises():
    graph = _chain_graph()
    try:
        apply_mutation(graph, "NOT_A_REAL_MUTATION", "evidence")
        assert False, "should have raised"
    except MutationError:
        pass


def test_mutation_on_missing_node_raises():
    graph = _chain_graph()
    try:
        apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "does-not-exist")
        assert False, "should have raised"
    except MutationError:
        pass


def test_diff_engine_reports_status_changes_only():
    base = _chain_graph()
    simulated = base.clone()
    apply_mutation(simulated, MutationType.REMOVE_EVIDENCE.value, "evidence")
    propagate_failure(simulated, "evidence")
    diff = compute_diff(base, simulated)
    changed_ids = {c["node_id"] for c in diff["changed_nodes"]}
    assert "evidence" in changed_ids
    assert diff["changed_node_count"] >= 4


def test_recovery_options_are_generated_and_require_approval():
    graph = _chain_graph()
    apply_mutation(graph, MutationType.REMOVE_EVIDENCE.value, "evidence")
    result = propagate_failure(graph, "evidence")
    br = compute_blast_radius(graph, "evidence", result)
    affected_dicts = [
        {"node_id": a.node_id, "node_type": a.node_type, "label": a.label,
         "impact_types": a.impact_types, "path_from_root": a.path_from_root}
        for a in result.affected
    ]
    options = generate_recovery_options(affected_dicts, br)
    assert len(options) > 0
    assert all(o["human_approval_required"] is True for o in options)


def test_full_runner_end_to_end_is_non_destructive():
    graph = _chain_graph()
    snapshot_data = graph.to_dict()
    original_json = SimGraph.from_snapshot_data(snapshot_data).to_dict()

    result = run_simulation(snapshot_data, [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": "evidence"}])

    assert result["status"] == "COMPLETED"
    assert result["human_review_required"] is True
    assert result["blast_radius"]["total_affected_count"] == 4
    # base snapshot_data itself must remain untouched
    assert SimGraph.from_snapshot_data(snapshot_data).to_dict() == original_json


def test_multi_mutation_simulation_merges_impacts():
    graph = _chain_graph()
    snapshot_data = graph.to_dict()
    mutations = [
        {"mutation_type": "REMOVE_EVIDENCE", "target_node_id": "evidence"},
        {"mutation_type": "BLOCK_OBLIGATION", "target_node_id": "obligation"},
    ]
    result = run_simulation(snapshot_data, mutations)
    assert result["status"] == "COMPLETED"
    assert len(result["mutations_applied"]) == 2
    hearing_affected = next(a for a in result["affected_nodes"] if a["node_id"] == "hearing")
    assert hearing_affected["new_status"] in ("BLOCKED", "REQUIRES_HUMAN_REVIEW")
