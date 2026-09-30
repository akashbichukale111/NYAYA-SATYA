from tests.conftest import get_case_by_key


def test_case_c_has_a_pending_deadline_conflict(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_C")
    r = seeded_client.get(f"/api/cases/{case['id']}/conflicts")
    conflicts = r.json()
    assert len(conflicts) >= 1
    conflict = conflicts[0]
    assert conflict["conflict_type"] == "deadline_conflict"
    assert conflict["human_review_status"] == "pending"
    assert conflict["source_a_event_id"] != conflict["source_b_event_id"]
    # Never assigns fraud/guilt language
    for banned in ("fraud", "perjury", "guilt", "lying"):
        assert banned not in conflict["possible_explanation"].lower()


def test_resolving_a_conflict_updates_its_status(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_C")
    conflict = seeded_client.get(f"/api/cases/{case['id']}/conflicts").json()[0]
    r = seeded_client.post(
        f"/api/cases/{case['id']}/conflicts/{conflict['id']}/resolve",
        json={"resolution_note": "Registry notice takes precedence.", "reviewer": "advocate-1"},
    )
    assert r.status_code == 200
    updated = seeded_client.get(f"/api/cases/{case['id']}/conflicts").json()
    assert next(c for c in updated if c["id"] == conflict["id"])["human_review_status"] == "resolved"
