def test_version_numbers_are_contiguous_after_commits(client):
    r = client.post("/api/cases", json={"title": "Versioning Test"})
    case_id = r.json()["id"]

    # A confident, unambiguous NEW deadline auto-commits (no existing open deadline yet).
    r = client.post(
        f"/api/cases/{case_id}/ingest",
        files={"file": ("f1.txt", b"Filing submitted. Reply due on or before 01 Jan 2027.", "text/plain")},
    )
    body = r.json()
    assert body["committed_versions"] == [1] or body["committed_versions"] == []
    # Either it auto-committed to v1, or it required review and stayed at v0.
    r = client.get(f"/api/cases/{case_id}/versions")
    versions = [v["version_number"] for v in r.json()]
    assert versions == list(range(len(versions)))  # contiguous 0..N, no gaps


def test_state_endpoint_reflects_latest_version(client):
    r = client.post("/api/cases", json={"title": "State Reflect Test"})
    case_id = r.json()["id"]
    r = client.get(f"/api/cases/{case_id}/state")
    assert r.status_code == 200
    assert r.json()["current_version_number"] == 0
    assert r.json()["snapshot"]["case_id"] == case_id
