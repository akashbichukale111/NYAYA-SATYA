import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.conftest import ADVOCATE_HEADERS, CITIZEN_HEADERS, create_case, upload_text_document


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_case_creation_and_retrieval(client):
    case = create_case(client)
    resp = client.get(f"/api/cases/{case['id']}", headers=ADVOCATE_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["case_reference"] == "TEST-001"


def test_case_not_found_returns_404(client):
    resp = client.get("/api/cases/nonexistent-case-id", headers=ADVOCATE_HEADERS)
    assert resp.status_code == 404


def test_document_upload_and_extraction(client):
    case = create_case(client)
    resp = upload_text_document(
        client, case["id"], "arrest.txt",
        "The accused was arrested on 5 January 2026. Remanded to judicial custody on 6 January 2026.",
    )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["status"] == "PARSED"

    custody = client.get(f"/api/cases/{case['id']}/custody", headers=ADVOCATE_HEADERS).json()
    assert len(custody["custody_events"]) >= 1
    for e in custody["custody_events"]:
        assert e["source_document_id"] == doc["id"]
        assert e["verification_status"] == "SOURCE_FACT"


def test_case_isolation_across_cases(client):
    case1 = create_case(client, ref="ISO-A")
    case2 = create_case(client, ref="ISO-B")
    upload_text_document(client, case1["id"], "a.txt", "The accused was arrested on 1 January 2026.")
    upload_text_document(client, case2["id"], "b.txt", "The accused was arrested on 2 January 2026.")

    custody1 = client.get(f"/api/cases/{case1['id']}/custody", headers=ADVOCATE_HEADERS).json()
    custody2 = client.get(f"/api/cases/{case2['id']}/custody", headers=ADVOCATE_HEADERS).json()

    assert all(e["case_id"] == case1["id"] for e in custody1["custody_events"])
    assert all(e["case_id"] == case2["id"] for e in custody2["custody_events"])
    ids1 = {e["id"] for e in custody1["custody_events"]}
    ids2 = {e["id"] for e in custody2["custody_events"]}
    assert ids1.isdisjoint(ids2)


def test_conflicting_custody_dates_produce_conflict_and_review_task(client):
    case = create_case(client, ref="CONFLICT-001")
    upload_text_document(client, case["id"], "station.txt",
                          "The accused was arrested on 12 February 2026 as per the station diary.")
    upload_text_document(client, case["id"], "prison.txt",
                          "The accused was arrested on 14 February 2026 according to the intake register.")

    conflicts = client.get(f"/api/cases/{case['id']}/conflicts", headers=ADVOCATE_HEADERS).json()
    assert len(conflicts["conflicts"]) == 1
    assert conflicts["conflicts"][0]["status"] == "OPEN"

    attention = client.get(f"/api/cases/{case['id']}/attention", headers=ADVOCATE_HEADERS).json()
    categories = [a["category"] for a in attention["attention_items"]]
    assert "CONFLICTING_CUSTODY_INFORMATION" in categories


def test_review_gate_approve_flow(client):
    case = create_case(client, ref="REVIEW-001")
    upload_text_document(client, case["id"], "station.txt",
                          "The accused was arrested on 12 February 2026.")
    upload_text_document(client, case["id"], "prison.txt",
                          "The accused was arrested on 14 February 2026.")
    conflicts = client.get(f"/api/cases/{case['id']}/conflicts", headers=ADVOCATE_HEADERS).json()
    conflict_id = conflicts["conflicts"][0]["id"]

    resp = client.post(f"/api/conflicts/{conflict_id}/resolve",
                        params={"resolved_value": "2026-02-12", "note": "station diary is authoritative"},
                        headers=ADVOCATE_HEADERS)
    assert resp.status_code == 200
    updated = client.get(f"/api/cases/{case['id']}/conflicts", headers=ADVOCATE_HEADERS).json()
    assert updated["conflicts"][0]["status"] == "RESOLVED_BY_HUMAN"


def test_rbac_citizen_cannot_create_case(client):
    resp = client.post("/api/cases", json={
        "case_reference": "RBAC-001", "title": "Test", "person_full_name": "X",
    }, headers=CITIZEN_HEADERS)
    assert resp.status_code == 403


def test_rbac_citizen_cannot_upload_document(client):
    case = create_case(client)
    resp = upload_text_document(client, case["id"], "x.txt", "text", headers=CITIZEN_HEADERS)
    assert resp.status_code == 403


def test_manual_event_is_user_reported_not_source_fact(client):
    case = create_case(client, ref="MANUAL-001")
    resp = client.post(f"/api/cases/{case['id']}/custody-events/manual", json={
        "event_type": "CUSTODY_STATUS_UPDATED", "event_date": "2026-03-01",
        "date_type": "USER_ENTERED_DATE", "notes": "Family reported update.",
    }, headers=ADVOCATE_HEADERS)
    assert resp.status_code == 200
    custody = client.get(f"/api/cases/{case['id']}/custody", headers=ADVOCATE_HEADERS).json()
    event = next(e for e in custody["custody_events"] if e["id"] == resp.json()["id"])
    assert event["verification_status"] == "USER_REPORTED"


def test_integration_adapter_never_asserts_currently_free(client):
    case = create_case(client, ref="RELEASE-001")
    upload_text_document(client, case["id"], "release_report.txt",
                          "Family reports release of the accused from custody.")
    twin = client.get(f"/api/cases/{case['id']}/integration/nyaya-satya", headers=ADVOCATE_HEADERS).json()
    # Must never claim a currently-free status string; only tracked via attention items
    # requiring human review.
    dump = str(twin)
    assert "CURRENTLY_FREE" not in dump
    assert any(a["category"] == "UNVERIFIED_RELEASE_EVENT" for a in twin["attention_items"])
