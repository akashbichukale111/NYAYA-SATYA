def test_case_create_and_get(client):
    created = client.post("/api/cases", json={"title": "My Case", "description": "d"}).json()
    fetched = client.get(f"/api/cases/{created['id']}").json()
    assert fetched["id"] == created["id"]
    assert fetched["title"] == "My Case"


def test_get_unknown_case_404s(client):
    resp = client.get("/api/cases/does-not-exist")
    assert resp.status_code == 404


def test_demo_seed_a_produces_strong_chain(client):
    case = client.post("/api/cases/demo/seed/A", json={}).json()
    assert case["is_demo"] is True
    cov = client.get(f"/api/cases/{case['id']}/coverage").json()
    assert cov["claims_total"] == 1
    assert cov["claims_with_evidence"] == 1
    # 3 independent documents support the single claim -> not single-source
    assert cov["single_source_claims"] == 0


def test_demo_seed_b_produces_single_point_dependency(client):
    case = client.post("/api/cases/demo/seed/B", json={}).json()
    fragility = client.get(f"/api/cases/{case['id']}/fragility").json()
    assert any(f["criticality"] == "SINGLE_POINT_DEPENDENCY" for f in fragility)


def test_demo_seed_c_produces_conflict(client):
    case = client.post("/api/cases/demo/seed/C", json={}).json()
    cov = client.get(f"/api/cases/{case['id']}/coverage").json()
    assert cov["conflicting_claims"] == 1


def test_unknown_demo_key_404s(client):
    resp = client.post("/api/cases/demo/seed/Z", json={})
    assert resp.status_code == 404


def test_review_gate_approval_flow(client):
    case = client.post("/api/cases", json={"title": "Review Case"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc"}).json()

    # simulate an agent proposing a consequential change via the review API directly
    # is not exposed as a public endpoint (agents call the service internally);
    # here we verify the queue + decide endpoints work end-to-end using the
    # service layer through a raw import, mirroring what an agent would do.
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.core.db import SessionLocal
    from app.services.review_service import propose_action

    db = SessionLocal()
    task = propose_action(
        db, case["id"], action_type="CHANGE_VERIFIED_STATUS", target_type="EVIDENCE",
        target_id=ev["id"], proposed_change={"verification_status": "VERIFIED"},
        proposing_agent="VerificationAgent",
    )
    db.close()

    queue = client.get(f"/api/cases/{case['id']}/review-queue").json()
    assert any(t["id"] == task.id for t in queue)

    resp = client.post(f"/api/reviews/{task.id}/approve", json={"note": "looks right"})
    assert resp.json()["status"] == "APPROVED"

    updated = client.get(f"/api/evidence/{ev['id']}").json()
    assert updated["verification_status"] == "VERIFIED"

    # audit trail must show both the proposal and the approval
    audit = client.get(f"/api/cases/{case['id']}/audit").json()
    actions = [a["action"] for a in audit]
    assert "PROPOSE_CHANGE_VERIFIED_STATUS" in actions
    assert "APPROVE_REVIEW" in actions


def test_evaluation_lab_runs_on_demo_case(client):
    case = client.post("/api/cases/demo/seed/A", json={}).json()
    result = client.get(f"/api/cases/{case['id']}/evaluation").json()
    assert result["case_id"] == case["id"]
    assert set(result["checks"].values()).issubset({"PASS", "FAIL", "NOT_RUN"})
    assert result["summary"]["fail_count"] == 0


def test_integration_summary_contract(client):
    case = client.post("/api/cases/demo/seed/B", json={}).json()
    summary = client.get(f"/api/cases/{case['id']}/integration-summary").json()
    for key in ("case_id", "evidence_count", "claim_count", "issue_count",
                "unsupported_claims", "unsupported_issues", "conflicting_claims",
                "critical_dependencies", "impact_items", "verification_pending",
                "provenance_refs", "attention_items", "last_updated"):
        assert key in summary
    assert len(summary["critical_dependencies"]) >= 1
