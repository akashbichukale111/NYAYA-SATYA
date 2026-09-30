import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.conftest import ADVOCATE_HEADERS, create_case, upload_text_document


def test_simulation_never_mutates_production_state(client):
    """
    Regression test for a real bug found during development: calling
    db.commit() inside the recompute helpers (reconciliation/attention/
    dependency) while running inside a Simulation/Crash Test SAVEPOINT
    silently committed the mutation to the real database and broke the
    rollback guarantee. This test fails loudly if that regresses.
    """
    case = create_case(client, ref="CRASHTEST-001")
    upload_text_document(client, case["id"], "order.txt", "Order issued granting release on furnishing surety.")

    orders_before = client.get(f"/api/cases/{case['id']}/orders", headers=ADVOCATE_HEADERS).json()["orders"]
    assert len(orders_before) == 1
    order_id = orders_before[0]["id"]

    resp = client.post(f"/api/cases/{case['id']}/crash-test", json={
        "event_type": "REMOVE_ORDER", "target_entity_id": order_id,
    }, headers=ADVOCATE_HEADERS)
    assert resp.status_code == 200
    result = resp.json()
    assert result["production_state_mutated"] is False
    # The simulated 'after' twin should show the order gone...
    assert not any(o["id"] == order_id for o in result["after"]["recent_orders"])

    # ...but the REAL data must be completely untouched.
    orders_after = client.get(f"/api/cases/{case['id']}/orders", headers=ADVOCATE_HEADERS).json()["orders"]
    assert len(orders_after) == 1
    assert orders_after[0]["id"] == order_id


def test_crash_test_conflicting_date_injection_does_not_persist(client):
    case = create_case(client, ref="CRASHTEST-002")
    upload_text_document(client, case["id"], "arrest.txt", "The accused was arrested on 1 January 2026.")
    events_before = client.get(f"/api/cases/{case['id']}/custody", headers=ADVOCATE_HEADERS).json()["custody_events"]
    assert len(events_before) == 1
    event_id = events_before[0]["id"]

    resp = client.post(f"/api/cases/{case['id']}/crash-test", json={
        "event_type": "INTRODUCE_CONFLICTING_CUSTODY_DATE", "target_entity_id": event_id,
    }, headers=ADVOCATE_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["production_state_mutated"] is False

    events_after = client.get(f"/api/cases/{case['id']}/custody", headers=ADVOCATE_HEADERS).json()["custody_events"]
    assert len(events_after) == 1  # simulated conflicting event must NOT persist

    conflicts_after = client.get(f"/api/cases/{case['id']}/conflicts", headers=ADVOCATE_HEADERS).json()["conflicts"]
    assert len(conflicts_after) == 0  # no real conflict should have been created


def test_missing_hearing_result_generates_attention(client):
    case = create_case(client, ref="MISSING-001")
    upload_text_document(client, case["id"], "notice.txt",
                          "A bail hearing was listed on 1 January 2020 to consider the application.")
    attention = client.get(f"/api/cases/{case['id']}/attention", headers=ADVOCATE_HEADERS).json()
    categories = [a["category"] for a in attention["attention_items"]]
    assert "PAST_TRACKED_DATE" in categories
    assert "MISSING_HEARING_RESULT" in categories


def test_time_machine_snapshot_and_diff(client):
    case = create_case(client, ref="TIMEMACHINE-001")
    tm_initial = client.get(f"/api/cases/{case['id']}/time-machine", headers=ADVOCATE_HEADERS).json()
    assert len(tm_initial["snapshots"]) >= 1  # snapshot taken at case creation

    upload_text_document(client, case["id"], "arrest.txt", "The accused was arrested on 1 January 2026.")
    tm_after = client.get(f"/api/cases/{case['id']}/time-machine", headers=ADVOCATE_HEADERS).json()
    assert len(tm_after["snapshots"]) >= 2

    first_id = tm_after["snapshots"][0]["id"]
    last_id = tm_after["snapshots"][-1]["id"]
    diff_resp = client.get(f"/api/cases/{case['id']}/time-machine", params={
        "compare_a": first_id, "compare_b": last_id,
    }, headers=ADVOCATE_HEADERS).json()
    assert "diff" in diff_resp
    assert diff_resp["diff"].get("custody_event_count", {}).get("after", 0) >= 1


def test_unknown_date_never_fabricated_end_to_end(client):
    case = create_case(client, ref="UNKNOWN-DATE-001")
    upload_text_document(client, case["id"], "vague.txt", "The accused was arrested.")
    custody = client.get(f"/api/cases/{case['id']}/custody", headers=ADVOCATE_HEADERS).json()
    assert len(custody["custody_events"]) == 1
    assert custody["custody_events"][0]["event_date"] is None
    assert custody["custody_events"][0]["date_type"] == "UNKNOWN_DATE"
