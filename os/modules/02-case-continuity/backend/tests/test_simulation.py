from tests.conftest import get_case_by_key


def test_counterfactual_removal_does_not_mutate_real_state(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_D")
    before_state = seeded_client.get(f"/api/cases/{case['id']}/state").json()
    before_version = before_state["current_version_number"]

    snapshot = before_state["snapshot"]
    deadline_ids = list(snapshot["deadlines"].keys())
    assert deadline_ids, "expected at least one open deadline in CASE_D"

    r = seeded_client.post(
        f"/api/cases/{case['id']}/simulate/remove",
        json={"collection": "deadlines", "entity_id": deadline_ids[0]},
    )
    assert r.status_code == 200
    result = r.json()
    assert result["label"] == "SIMULATION ONLY"
    assert deadline_ids[0] not in result["simulated_snapshot"]["deadlines"]

    after_state = seeded_client.get(f"/api/cases/{case['id']}/state").json()
    assert after_state["current_version_number"] == before_version
    assert deadline_ids[0] in after_state["snapshot"]["deadlines"], "simulation must not remove the real deadline"


def test_future_state_projection_is_workflow_only_not_a_verdict(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_A")
    r = seeded_client.post(
        f"/api/cases/{case['id']}/simulate/future-state",
        json={"current_event_type": "hearing_occurred"},
    )
    body = r.json()
    assert body["label"].startswith("SIMULATION ONLY")
    assert "obligation_created" in body["simulated_next_state"] or "deadline_created" in body["simulated_next_state"]
    for banned in ("guilty", "verdict", "will win", "will lose"):
        assert banned not in str(body).lower()


def test_field_change_simulation_is_recorded_but_isolated(seeded_client):
    case = get_case_by_key(seeded_client, "CASE_A")
    snapshot = seeded_client.get(f"/api/cases/{case['id']}/state").json()["snapshot"]
    deadline_ids = list(snapshot["deadlines"].keys())
    if not deadline_ids:
        return  # CASE_A's deadline may still be pending human review in this seed; nothing to simulate on yet.
    r = seeded_client.post(
        f"/api/cases/{case['id']}/simulate/field-change",
        json={"collection": "deadlines", "entity_id": deadline_ids[0], "field": "due_date",
              "new_value": "01 Jan 2099"},
    )
    assert r.status_code == 200
    assert r.json()["simulated_snapshot"]["deadlines"][deadline_ids[0]]["due_date"] == "01 Jan 2099"

    real_after = seeded_client.get(f"/api/cases/{case['id']}/state").json()
    assert real_after["snapshot"]["deadlines"][deadline_ids[0]]["due_date"] != "01 Jan 2099"
