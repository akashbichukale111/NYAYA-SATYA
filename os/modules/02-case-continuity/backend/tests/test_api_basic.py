def test_healthz(client):
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["llm_provider"] == "mock"


def test_create_case_and_initial_version(client):
    r = client.post("/api/cases", json={"title": "Test Case", "parties": [{"name": "A", "role": "petitioner"}]})
    assert r.status_code == 200
    case_id = r.json()["id"]

    r = client.get(f"/api/cases/{case_id}")
    assert r.status_code == 200
    assert r.json()["current_version_number"] == 0
    assert len(r.json()["parties"]) == 1

    r = client.get(f"/api/cases/{case_id}/versions")
    versions = r.json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 0
    assert versions[0]["label"] == "Initial intake"


def test_ingest_document_creates_events_and_proposals(client):
    r = client.post("/api/cases", json={"title": "Ingestion Test"})
    case_id = r.json()["id"]

    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("filing.txt", b"Filing submitted. Reply due on or before 12 Oct 2026.", "text/plain")},
        data={"doc_type_hint": "filing"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["document_id"]
    assert len(body["proposals"]) >= 1

    r = client.get(f"/api/cases/{case_id}/events")
    events = r.json()
    types = [e["event_type"] for e in events]
    assert "case_created" in types
    assert "document_uploaded" in types
    assert "agent_action" in types  # extraction event


def test_unknown_case_returns_404(client):
    r = client.get("/api/cases/does-not-exist/state")
    assert r.status_code == 404
