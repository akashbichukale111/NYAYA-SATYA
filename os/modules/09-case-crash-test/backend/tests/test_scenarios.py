"""
Scenario Tests: one deterministic test per major crash-scenario category
from the taxonomy, run through the full runner.
"""
from app.simulation_engine.runner import run_simulation

BASE = {
    "nodes": [
        {"id": "doc1", "node_type": "DOCUMENT", "label": "Filing Annexure", "status": "VERIFIED", "attributes": {}},
        {"id": "ev1", "node_type": "EVIDENCE", "label": "Device Log", "status": "VERIFIED", "attributes": {}},
        {"id": "claim1", "node_type": "CLAIM", "label": "Timeline Claim", "status": "VERIFIED", "attributes": {}},
        {"id": "issue1", "node_type": "ISSUE", "label": "Timeline Issue", "status": "KNOWN", "attributes": {}},
        {"id": "ob1", "node_type": "OBLIGATION", "label": "Disclosure Obligation", "status": "KNOWN", "attributes": {}},
        {"id": "dl1", "node_type": "DEADLINE", "label": "Filing Deadline", "status": "KNOWN", "attributes": {}},
        {"id": "hr1", "node_type": "HEARING", "label": "Status Hearing", "status": "VERIFIED", "attributes": {}},
        {"id": "or1", "node_type": "ORDER", "label": "Procedural Order", "status": "VERIFIED", "attributes": {}},
        {"id": "rd1", "node_type": "REGISTRY_DEFECT", "label": "Registry Check", "status": "KNOWN", "attributes": {}},
        {"id": "cu1", "node_type": "CUSTODY_EVENT", "label": "Custody Event", "status": "VERIFIED", "attributes": {}},
        {"id": "wf1", "node_type": "WORKFLOW", "label": "Intake Workflow", "status": "KNOWN", "attributes": {}},
        {"id": "prov1", "node_type": "DOCUMENT", "label": "Source Reference Doc", "status": "VERIFIED", "attributes": {}},
    ],
    "relationships": [
        {"id": "r1", "source_id": "claim1", "target_id": "ev1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r2", "source_id": "issue1", "target_id": "claim1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r3", "source_id": "ob1", "target_id": "issue1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r4", "source_id": "dl1", "target_id": "ob1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r5", "source_id": "wf1", "target_id": "hr1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r6", "source_id": "hr1", "target_id": "or1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r7", "source_id": "rd1", "target_id": "doc1", "rel_type": "DEPENDS_ON", "attributes": {}},
        {"id": "r8", "source_id": "cu1", "target_id": "prov1", "rel_type": "DEPENDS_ON", "attributes": {}},
    ],
}


def _run(mutation_type, target):
    result = run_simulation(BASE, [{"mutation_type": mutation_type, "target_node_id": target}])
    assert result["status"] == "COMPLETED", result
    return result


def test_evidence_removal_cascades_to_obligation_and_deadline():
    result = _run("REMOVE_EVIDENCE", "ev1")
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert {"claim1", "issue1", "ob1", "dl1"} <= ids


def test_document_removal():
    result = _run("REMOVE_DOCUMENT", "doc1")
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert "rd1" in ids


def test_claim_contradiction():
    result = _run("CONTRADICT_CLAIM", "claim1")
    claim_node = next(n for n in result["simulated_state"]["nodes"] if n["id"] == "claim1")
    assert claim_node["status"] == "CONFLICTING"
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert "issue1" in ids


def test_obligation_block_cascades_to_deadline():
    result = _run("BLOCK_OBLIGATION", "ob1")
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert "dl1" in ids
    dl_node = next(a for a in result["affected_nodes"] if a["node_id"] == "dl1")
    assert dl_node["new_status"] == "BLOCKED"


def test_deadline_unknown():
    result = _run("MARK_DATE_UNKNOWN", "dl1")
    dl_node = next(n for n in result["simulated_state"]["nodes"] if n["id"] == "dl1")
    assert dl_node["status"] == "UNKNOWN"


def test_hearing_result_missing_cascades_to_order_and_workflow():
    result = _run("REMOVE_HEARING_RESULT", "hr1")
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert "wf1" in ids


def test_order_supersession():
    result = _run("SUPERSEDE_ORDER", "or1")
    or_node = next(n for n in result["simulated_state"]["nodes"] if n["id"] == "or1")
    assert or_node["status"] == "SUPERSEDED"
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert "hr1" in ids


def test_registry_defect_introduction():
    result = _run("INTRODUCE_DEFECT", "rd1")
    rd_node = next(n for n in result["simulated_state"]["nodes"] if n["id"] == "rd1")
    assert rd_node["status"] == "REQUIRES_HUMAN_REVIEW"


def test_custody_conflict_never_infers_detention_status():
    result = _run("CREATE_CUSTODY_CONFLICT", "cu1")
    cu_node = next(n for n in result["simulated_state"]["nodes"] if n["id"] == "cu1")
    assert cu_node["status"] == "CONFLICTING"
    # The engine must never attach a legal/detention verdict field.
    assert "detention_status" not in cu_node.get("attributes", {})
    assert "legal_outcome" not in result


def test_workflow_failure():
    result = _run("BLOCK_ACTION", "wf1")
    wf_node = next(n for n in result["simulated_state"]["nodes"] if n["id"] == "wf1")
    assert wf_node["status"] == "BLOCKED"


def test_provenance_failure_cascades_to_custody_event():
    result = _run("BREAK_PROVENANCE_CHAIN", "prov1")
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert "cu1" in ids


def test_multi_failure_combines_independent_chains():
    mutations = [
        {"mutation_type": "MARK_EVIDENCE_UNVERIFIED", "target_node_id": "ev1"},
        {"mutation_type": "SUPERSEDE_ORDER", "target_node_id": "or1"},
        {"mutation_type": "REMOVE_HEARING_RESULT", "target_node_id": "hr1"},
        {"mutation_type": "BLOCK_ACTION", "target_node_id": "wf1"},
    ]
    result = run_simulation(BASE, mutations)
    assert result["status"] == "COMPLETED"
    assert len(result["mutations_applied"]) == 4
    ids = {a["node_id"] for a in result["affected_nodes"]}
    assert {"claim1", "issue1", "ob1", "dl1"} <= ids


def test_engine_never_emits_legal_outcome_fields():
    """
    Blanket structural guard: no simulation result may contain any of the
    forbidden legal-outcome vocabulary as a key or as a node status value.
    """
    result = _run("REMOVE_EVIDENCE", "ev1")
    forbidden_terms = ["conviction", "acquittal", "bail_outcome", "guilt", "innocence", "verdict"]
    import json
    blob = json.dumps(result).lower()
    for term in forbidden_terms:
        assert term not in blob
