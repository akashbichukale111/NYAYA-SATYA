def test_coverage_metrics_empty_case(client):
    case = client.post("/api/cases", json={"title": "Empty Case"}).json()
    cov = client.get(f"/api/cases/{case['id']}/coverage").json()
    assert cov["claims_total"] == 0
    assert cov["issues_total"] == 0
    assert cov["evidence_items_total"] == 0


def test_missing_evidence_detected_for_unsupported_claim(client):
    case = client.post("/api/cases", json={"title": "C1"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Unsupported claim"}).json()
    missing = client.get(f"/api/cases/{case['id']}/missing-evidence").json()
    ids = [c["claim_id"] for c in missing["claims_without_evidence"]]
    assert claim["id"] in ids


def test_single_point_dependency_detected(client):
    case = client.post("/api/cases", json={"title": "C2"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Only doc"}).json()
    claim1 = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Claim A"}).json()
    claim2 = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Claim B"}).json()

    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "EVIDENCE", "source_id": ev["id"],
        "target_type": "CLAIM", "target_id": claim1["id"],
        "relationship_type": "SUPPORTS",
    })
    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "EVIDENCE", "source_id": ev["id"],
        "target_type": "CLAIM", "target_id": claim2["id"],
        "relationship_type": "SUPPORTS",
    })

    fragility = client.get(f"/api/cases/{case['id']}/fragility").json()
    entry = [f for f in fragility if f["evidence_id"] == ev["id"]][0]
    assert entry["criticality"] == "SINGLE_POINT_DEPENDENCY"
    assert set(entry["affected_claims"]) == {claim1["id"], claim2["id"]}


def test_impact_traversal_reaches_issue_through_claim(client):
    case = client.post("/api/cases", json={"title": "C3"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Claim"}).json()
    issue = client.post(f"/api/cases/{case['id']}/issues", json={"question": "Issue?"}).json()

    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "EVIDENCE", "source_id": ev["id"],
        "target_type": "CLAIM", "target_id": claim["id"], "relationship_type": "SUPPORTS",
    })
    client.post(f"/api/cases/{case['id']}/relationships", json={
        "source_type": "CLAIM", "source_id": claim["id"],
        "target_type": "ISSUE", "target_id": issue["id"], "relationship_type": "REQUIRES",
    })

    impact = client.get(f"/api/evidence/{ev['id']}/impact").json()
    assert claim["id"] in impact["affected_claims"]
    assert issue["id"] in impact["affected_issues"]
    assert impact["criticality"] == "SINGLE_POINT_DEPENDENCY"
    assert impact["human_review_required"] is True
