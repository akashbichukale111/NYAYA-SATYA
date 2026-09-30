from tests.test_api import client, _ensure_tables  # noqa: F401  (reuses client + table fixture)


def _create_case():
    r = client.post("/api/cases", json={"title": "Section2 Case", "is_demo": True}, headers={"X-Role": "ADMIN"})
    return r.json()["id"]


def test_adapter_ingest_creates_workflow():
    case_id = _create_case()
    r = client.post(
        "/api/adapters/evidence_dependency/ingest",
        json={"case_id": case_id, "event_id": "adapter-evt-1"},
        headers={"X-Role": "ADVOCATE", "X-Case-Access": case_id},
    )
    assert r.status_code == 200
    assert r.json()["workflow_type"] == "evidence_gap"


def test_adapter_ingest_is_idempotent_on_event_id():
    case_id = _create_case()
    headers = {"X-Role": "ADVOCATE", "X-Case-Access": case_id}
    body = {"case_id": case_id, "event_id": "adapter-evt-dup"}
    r1 = client.post("/api/adapters/evidence_dependency/ingest", json=body, headers=headers)
    r2 = client.post("/api/adapters/evidence_dependency/ingest", json=body, headers=headers)
    assert r1.json()["id"] == r2.json()["workflow_id"]


def test_unknown_adapter_name_rejected():
    case_id = _create_case()
    r = client.post(
        "/api/adapters/not_a_real_adapter/ingest",
        json={"case_id": case_id},
        headers={"X-Role": "ADVOCATE", "X-Case-Access": case_id},
    )
    assert r.status_code == 400


def test_undertrial_liberty_adapter_never_auto_creates_workflow():
    """Liberty-related signals never map to an automated template."""
    case_id = _create_case()
    r = client.post(
        "/api/adapters/undertrial_liberty/ingest",
        json={"case_id": case_id, "event_id": "liberty-evt-1"},
        headers={"X-Role": "ADVOCATE", "X-Case-Access": case_id},
    )
    assert r.status_code == 200
    assert "human must create a workflow manually" in r.json()["detail"]


def test_conflict_visible_over_api():
    case_id = _create_case()
    headers = {"X-Role": "ADVOCATE", "X-Case-Access": case_id}
    client.post(f"/api/cases/{case_id}/workflows",
                json={"workflow_type": "deadline_preparation", "trigger_type": "TRACKED_DATE_APPROACHING"},
                headers=headers)
    client.post(f"/api/cases/{case_id}/workflows",
                json={"workflow_type": "registry_defect", "trigger_type": "REGISTRY_DEFECT_DETECTED"},
                headers=headers)
    r = client.get(f"/api/cases/{case_id}/conflicts", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "OPEN"


def test_stale_state_over_api():
    case_id = _create_case()
    headers = {"X-Role": "ADVOCATE", "X-Case-Access": case_id}
    r = client.post(f"/api/cases/{case_id}/workflows",
                     json={"workflow_type": "evidence_gap", "trigger_type": "MANUAL_TRIGGER"}, headers=headers)
    wf_id = r.json()["id"]

    # bump the case version to simulate an external change
    bump = client.post(f"/api/cases/{case_id}/bump-version?reason=test", headers={"X-Role": "ADMIN", "X-Case-Access": case_id})
    assert bump.status_code == 200
    assert bump.json()["state_version"] == 2


def test_simulate_over_api_does_not_change_real_workflow():
    case_id = _create_case()
    headers = {"X-Role": "ADVOCATE", "X-Case-Access": case_id}
    r = client.post(f"/api/cases/{case_id}/workflows",
                     json={"workflow_type": "evidence_gap", "trigger_type": "MANUAL_TRIGGER"}, headers=headers)
    wf_id = r.json()["id"]
    detail = client.get(f"/api/workflows/{wf_id}", headers=headers).json()
    first_task_id = detail["tasks"][0]["id"]

    sim = client.post(f"/api/workflows/{wf_id}/simulate/task-failure/{first_task_id}", headers=headers)
    assert sim.status_code == 200
    assert sim.json()["live_state_mutated"] is False

    after = client.get(f"/api/workflows/{wf_id}", headers=headers).json()
    assert after["workflow"]["status"] == "PLANNED"  # unchanged by the simulation


def test_recovery_options_over_api():
    case_id = _create_case()
    headers = {"X-Role": "PARALEGAL", "X-Case-Access": case_id}
    r = client.post(f"/api/cases/{case_id}/workflows",
                     json={"workflow_type": "evidence_gap", "trigger_type": "MANUAL_TRIGGER"}, headers=headers)
    wf_id = r.json()["id"]
    detail = client.get(f"/api/workflows/{wf_id}", headers=headers).json()
    first_task_id = detail["tasks"][0]["id"]

    client.post(f"/api/tasks/{first_task_id}/start", headers=headers)
    client.post(f"/api/tasks/{first_task_id}/fail", json={"reason": "api test failure"}, headers=headers)

    opts = client.get(f"/api/tasks/{first_task_id}/recovery-options", headers=headers)
    assert opts.status_code == 200
    assert len(opts.json()["options"]) == 4


def test_crash_test_endpoint_over_api():
    r = client.get("/api/crash-test/run", headers={"X-Role": "ADVOCATE"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_scenarios"] == 12
    assert body["evaluated"] + body["not_evaluated"] == 12
    assert "DEPENDENCY_DISAPPEARS" in body["confirmed_risks"]  # known gap, honestly surfaced


def test_crash_test_endpoint_denies_citizen():
    r = client.get("/api/crash-test/run", headers={"X-Role": "CITIZEN"})
    assert r.status_code == 403
