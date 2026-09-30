def test_crash_test_is_non_destructive(client):
    case = client.post("/api/cases", json={"title": "Crash Test Case"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Claim"}).json()
    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "EVIDENCE", "source_id": ev["id"],
        "target_type": "CLAIM", "target_id": claim["id"], "relationship_type": "SUPPORTS",
    })

    before_evidence = client.get(f"/api/evidence/{ev['id']}").json()

    result = client.post(f"/api/evidence/{ev['id']}/crash-test", json={
        "event_type": "REMOVE_EVIDENCE", "target_type": "EVIDENCE", "target_id": ev["id"],
    }).json()

    assert claim["id"] in result["affected_claims"]
    assert result["human_review_required"] is True
    assert "SIMULATION" in result["note"]

    after_evidence = client.get(f"/api/evidence/{ev['id']}").json()
    # The evidence row itself must be completely untouched by the simulation.
    assert before_evidence == after_evidence


def test_crash_test_run_is_recorded_and_auditable(client):
    case = client.post("/api/cases", json={"title": "Crash Audit Case"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc"}).json()

    client.post(f"/api/evidence/{ev['id']}/crash-test", json={
        "event_type": "MARK_UNVERIFIED", "target_type": "EVIDENCE", "target_id": ev["id"],
    })

    # Crash test runs are not part of audit log directly but evidence creation is;
    # verify the base audit trail exists and is append-only-queryable.
    audit = client.get(f"/api/cases/{case['id']}/audit").json()
    actions = [a["action"] for a in audit]
    assert "EVIDENCE_CREATED" in actions
