def test_new_deadline_signal_creates_deadline_proposal(client):
    r = client.post("/api/cases", json={"title": "Change Detection Test"})
    case_id = r.json()["id"]
    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("f.txt", b"Filing submitted. Reply due on or before 12 Oct 2026.", "text/plain")},
    )
    proposals = r.json()["proposals"]
    kinds = [(p["entity_type"], p["nature"]) for p in proposals]
    assert ("deadline", "new") in kinds


def test_ambiguous_document_flagged_for_review(client):
    r = client.post("/api/cases", json={"title": "Ambiguous Test"})
    case_id = r.json()["id"]
    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("f.txt", b"A general administrative note with no clear content.", "text/plain")},
    )
    proposals = r.json()["proposals"]
    assert any(p["nature"] == "ambiguous" and p["requires_human_review"] for p in proposals)


def test_pending_proposals_listable_and_reviewable(client):
    r = client.post("/api/cases", json={"title": "Review Gate Test"})
    case_id = r.json()["id"]
    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("f.txt", b"The court hereby orders that the respondent shall submit documents.",
                        "text/plain")},
    )
    proposals = r.json()["proposals"]
    obligation_proposal = next(p for p in proposals if p["entity_type"] == "obligation")
    assert obligation_proposal["requires_human_review"] is True
    assert obligation_proposal["review_status"] == "pending"

    r = client.post(
        f"/api/cases/{case_id}/proposals/{obligation_proposal['id']}/review",
        json={"decision": "approve", "reviewer": "advocate-1"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "committed"

    r = client.get(f"/api/cases/{case_id}/proposals", params={"status": "approved"})
    assert any(p["id"] == obligation_proposal["id"] for p in r.json())
