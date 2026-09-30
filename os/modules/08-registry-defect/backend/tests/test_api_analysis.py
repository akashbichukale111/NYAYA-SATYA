import io


def _setup_case_package(client, user):
    case_resp = client.post("/api/cases", json={"title": "C"}, headers={"X-User-Id": user.id})
    case_id = case_resp.json()["id"]
    pkg_resp = client.post(f"/api/cases/{case_id}/filing-packages", json={"name": "Pkg"},
                            headers={"X-User-Id": user.id})
    return case_id, pkg_resp.json()["id"]


def test_dependency_graph_endpoint(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, user)
    resp = client.get(f"/api/filing-packages/{pkg_id}/dependency-graph", headers={"X-User-Id": user.id})
    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body and "edges" in body


def test_dependency_graph_respects_case_isolation(client, make_user):
    owner = make_user(role="ADVOCATE")
    other = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, owner)
    resp = client.get(f"/api/filing-packages/{pkg_id}/dependency-graph", headers={"X-User-Id": other.id})
    assert resp.status_code == 403


def test_time_machine_endpoint(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, user)
    resp = client.get(f"/api/filing-packages/{pkg_id}/time-machine", headers={"X-User-Id": user.id})
    assert resp.status_code == 200
    assert "document_history" in resp.json()


def test_simulation_requires_capability(client, make_user):
    citizen = make_user(role="CITIZEN")
    case_id, pkg_id = _setup_case_package(client, citizen)
    resp = client.post(f"/api/filing-packages/{pkg_id}/simulation",
                        json={"scenario": "REMOVE_REQUIRED_DOCUMENT", "params": {}},
                        headers={"X-User-Id": citizen.id})
    assert resp.status_code == 403


def test_simulation_runs_for_legal_aid(client, make_user):
    legal_aid = make_user(role="LEGAL_AID")
    case_id, pkg_id = _setup_case_package(client, legal_aid)
    resp = client.post(f"/api/filing-packages/{pkg_id}/simulation",
                        json={"scenario": "REMOVE_REFERENCED_ANNEXURE", "params": {}},
                        headers={"X-User-Id": legal_aid.id})
    assert resp.status_code == 200
    assert resp.json()["recognized"] is True


def test_crash_test_requires_advocate_or_admin(client, make_user):
    legal_aid = make_user(role="LEGAL_AID")
    case_id, pkg_id = _setup_case_package(client, legal_aid)
    resp = client.post(f"/api/filing-packages/{pkg_id}/crash-test", headers={"X-User-Id": legal_aid.id})
    assert resp.status_code == 403


def test_crash_test_runs_for_advocate(client, make_user):
    advocate = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, advocate)
    resp = client.post(f"/api/filing-packages/{pkg_id}/crash-test", headers={"X-User-Id": advocate.id})
    assert resp.status_code == 200
    assert len(resp.json()["scenarios"]) == 12


def test_evaluation_endpoint_runs_real_suite(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, user)
    resp = client.get(f"/api/filing-packages/{pkg_id}/evaluation", headers={"X-User-Id": user.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(body["results"])
    assert body["fail_count"] == 0


def test_defect_verify_endpoint_and_impact_endpoint(client, make_user):
    advocate = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, advocate)
    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition"},
        files={"file": ("p.txt", io.BytesIO(b"References Annexure K which is absent."), "text/plain")},
        headers={"X-User-Id": advocate.id},
    )
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": advocate.id})
    defects = client.get(f"/api/filing-packages/{pkg_id}/defects", headers={"X-User-Id": advocate.id}).json()
    defect_id = defects[0]["id"]

    verify_resp = client.post(f"/api/defects/{defect_id}/verify", headers={"X-User-Id": advocate.id})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["result"] in ("VERIFIED", "STILL_FAILING", "UNKNOWN")

    impact_resp = client.get(f"/api/defects/{defect_id}/impact", headers={"X-User-Id": advocate.id})
    assert impact_resp.status_code == 200
    assert impact_resp.json()["found"] is True


def test_impact_endpoint_respects_case_isolation(client, make_user):
    owner = make_user(role="ADVOCATE")
    other = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, owner)
    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition"},
        files={"file": ("p.txt", io.BytesIO(b"References Annexure M which is absent."), "text/plain")},
        headers={"X-User-Id": owner.id},
    )
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": owner.id})
    defects = client.get(f"/api/filing-packages/{pkg_id}/defects", headers={"X-User-Id": owner.id}).json()
    defect_id = defects[0]["id"]

    resp = client.get(f"/api/defects/{defect_id}/impact", headers={"X-User-Id": other.id})
    assert resp.status_code == 403
