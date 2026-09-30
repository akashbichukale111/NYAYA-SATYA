from tests.conftest import get_case_by_key


def test_case_h_demonstrates_verification_failure(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_H")
    r = seeded_client.get(f"/api/cases/{case['id']}/audit")
    agent_runs = r.json()["agent_runs"]
    verification_runs = [a for a in agent_runs if a["agent_name"] == "VerificationAgent"]
    assert verification_runs
    assert any(a["output_summary"] == "failed" for a in verification_runs)


def test_rejecting_a_proposal_keeps_it_in_audit_history(client):
    r = client.post("/api/cases", json={"title": "Rejection Test"})
    case_id = r.json()["id"]
    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("f.txt", b"A general administrative note with no clear content.", "text/plain")},
    )
    proposal_id = r.json()["proposals"][0]["id"]

    r = client.post(f"/api/cases/{case_id}/proposals/{proposal_id}/review",
                     json={"decision": "reject", "reviewer": "advocate-1"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    proposals = client.get(f"/api/cases/{case_id}/proposals").json()
    rejected = next(p for p in proposals if p["id"] == proposal_id)
    assert rejected["review_status"] == "rejected"

    audit_trail = client.get(f"/api/cases/{case_id}/audit").json()["audit_trail"]
    assert any(a["event_type"] == "rejection" and a["source"] == proposal_id for a in audit_trail)


def test_cannot_review_an_already_reviewed_proposal_twice(client):
    r = client.post("/api/cases", json={"title": "Double Review Test"})
    case_id = r.json()["id"]
    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("f.txt", b"A general administrative note with no clear content.", "text/plain")},
    )
    proposal_id = r.json()["proposals"][0]["id"]
    client.post(f"/api/cases/{case_id}/proposals/{proposal_id}/review",
                json={"decision": "reject", "reviewer": "advocate-1"})
    r = client.post(f"/api/cases/{case_id}/proposals/{proposal_id}/review",
                     json={"decision": "approve", "reviewer": "advocate-2"})
    assert r.status_code == 400
