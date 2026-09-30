from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_case_with_chain(title="Test Case"):
    r = client.post("/api/cases", json={"title": title})
    assert r.status_code == 200
    case = r.json()
    case_id = case["id"]

    def node(node_type, label, status="KNOWN"):
        resp = client.post(f"/api/cases/{case_id}/nodes", json={
            "node_type": node_type, "label": label, "status": status,
        })
        assert resp.status_code == 200
        return resp.json()

    evidence = node("EVIDENCE", "Evidence E1", "VERIFIED")
    claim = node("CLAIM", "Claim C1", "VERIFIED")
    obligation = node("OBLIGATION", "Obligation O1", "KNOWN")

    def rel(source, target, rel_type):
        resp = client.post(f"/api/cases/{case_id}/relationships", json={
            "source_id": source["id"], "target_id": target["id"], "rel_type": rel_type,
        })
        assert resp.status_code == 200
        return resp.json()

    rel(claim, evidence, "DEPENDS_ON")
    rel(obligation, claim, "DEPENDS_ON")

    snap = client.post(f"/api/cases/{case_id}/snapshots", json={"label": "initial"})
    assert snap.status_code == 200

    return case_id, snap.json()["id"], evidence, claim, obligation


def test_full_case_lifecycle_and_simulation():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain()

    sim_resp = client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    })
    assert sim_resp.status_code == 200
    sim = sim_resp.json()
    assert sim["status"] == "COMPLETED"
    assert sim["human_review_required"] is True

    blast = client.get(f"/api/simulations/{sim['id']}/blast-radius").json()
    assert claim["id"] in blast["affected_claims"]
    assert obligation["id"] in blast["affected_obligations"]

    diff = client.get(f"/api/simulations/{sim['id']}/diff").json()
    assert diff["changed_node_count"] >= 2

    recovery = client.get(f"/api/simulations/{sim['id']}/recovery-options").json()
    assert len(recovery) > 0

    tree = client.get(f"/api/simulations/{sim['id']}/failure-tree").json()
    assert tree[0]["root_failure"] == evidence["id"]


def test_production_graph_unchanged_after_simulation():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Isolation Case")

    before = client.get(f"/api/cases/{case_id}/graph").json()
    evidence_status_before = next(n["status"] for n in before["nodes"] if n["id"] == evidence["id"])
    assert evidence_status_before == "VERIFIED"

    client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    })

    after = client.get(f"/api/cases/{case_id}/graph").json()
    evidence_status_after = next(n["status"] for n in after["nodes"] if n["id"] == evidence["id"])
    # The REAL graph must be untouched by the simulation.
    assert evidence_status_after == "VERIFIED"
    assert evidence_status_after == evidence_status_before


def test_case_isolation_across_two_cases():
    case_a_id, snap_a, ev_a, claim_a, ob_a = _make_case_with_chain("Case A")
    case_b_id, snap_b, ev_b, claim_b, ob_b = _make_case_with_chain("Case B")

    graph_a = client.get(f"/api/cases/{case_a_id}/graph").json()
    ids_a = {n["id"] for n in graph_a["nodes"]}
    assert ev_b["id"] not in ids_a
    assert claim_b["id"] not in ids_a


def test_review_queue_and_approval_flow():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Review Case")
    sim = client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    }).json()
    assert sim["human_review_required"] is True

    queue = client.get(f"/api/cases/{case_id}/review-queue").json()
    assert len(queue) > 0

    review_id = queue[0]["id"]
    approved = client.post(
        f"/api/reviews/{review_id}/approve",
        json={"decided_by": "tester"},
        headers={"X-User-Role": "REVIEWER"},
    ).json()
    assert approved["status"] == "APPROVED"

    queue_after = client.get(f"/api/cases/{case_id}/review-queue").json()
    assert review_id not in {r["id"] for r in queue_after}


def test_audit_trail_records_events():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Audit Case")
    client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    })
    audit = client.get(f"/api/cases/{case_id}/audit").json()
    event_types = {e["event_type"] for e in audit}
    assert "CASE_CREATED" in event_types
    assert "SNAPSHOT_CREATED" in event_types
    assert "SIMULATION_RUN" in event_types


def test_scenario_comparison_endpoint():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Compare Case")
    sim_a = client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    }).json()
    sim_b = client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "MARK_EVIDENCE_UNVERIFIED", "target_node_id": evidence["id"]}],
    }).json()

    cmp_resp = client.post(f"/api/simulations/{sim_a['id']}/compare", json={
        "simulation_id_a": sim_a["id"], "simulation_id_b": sim_b["id"],
    })
    assert cmp_resp.status_code == 200
    cmp = cmp_resp.json()
    assert "note" in cmp and "No legal or outcome ranking" in cmp["note"]


def test_recovery_simulation_does_not_touch_real_case():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Recovery Case")
    sim = client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    }).json()

    recovery = client.post(f"/api/simulations/{sim['id']}/recovery-simulation", json={
        "additional_mutations": [{"mutation_type": "MARK_EVIDENCE_UNVERIFIED", "target_node_id": evidence["id"]}],
    })
    assert recovery.status_code == 200
    body = recovery.json()
    assert "recovery SIMULATION only" in body["note"]

    real_graph = client.get(f"/api/cases/{case_id}/graph").json()
    ev_status = next(n["status"] for n in real_graph["nodes"] if n["id"] == evidence["id"])
    assert ev_status == "VERIFIED"


def test_demo_load_and_disclaimer_present():
    resp = client.post("/api/demo/load")
    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == "DEMONSTRATION DATA — NOT A REAL CASE"
    assert len(body["cases"]) == 4


def test_demo_evidence_collapse_scenario_via_api():
    load_resp = client.post("/api/demo/load").json()
    demo_a = next(c for c in load_resp["cases"] if "Evidence Collapse" in c["title"])
    case_id = demo_a["id"]

    graph = client.get(f"/api/cases/{case_id}/graph").json()
    evidence_node = next(n for n in graph["nodes"] if n["node_type"] == "EVIDENCE")

    snapshots = client.get(f"/api/cases/{case_id}/snapshots").json()
    snapshot_id = snapshots[0]["id"]

    sim = client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence_node["id"]}],
    }).json()
    assert sim["status"] == "COMPLETED"
    blast = sim["result"]["blast_radius"]
    assert blast["total_affected_count"] >= 4  # 2 claims + issue + obligation + hearing in Demo A


def test_evaluation_lab_returns_pass_fail_not_run_only():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Eval Case")
    resp = client.get(f"/api/cases/{case_id}/evaluation")
    assert resp.status_code == 200
    body = resp.json()
    allowed = {"PASS", "FAIL", "NOT_RUN"}
    for test in body["tests"]:
        assert test["status"] in allowed


def test_integration_summary_shape():
    case_id, snapshot_id, evidence, claim, obligation = _make_case_with_chain("Integration Case")
    client.post(f"/api/cases/{case_id}/simulations", json={
        "base_snapshot_id": snapshot_id,
        "inline_mutations": [{"mutation_type": "REMOVE_EVIDENCE", "target_node_id": evidence["id"]}],
    })
    resp = client.get(f"/api/cases/{case_id}/integration-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert claim["id"] in body["affected_claims"]


def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
