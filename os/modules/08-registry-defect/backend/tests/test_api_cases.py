def test_create_case_requires_user_header(client):
    resp = client.post("/api/cases", json={"title": "My Case"})
    assert resp.status_code == 401


def test_create_and_get_case(client, make_user):
    user = make_user(role="ADVOCATE")
    resp = client.post("/api/cases", json={"title": "My Case"}, headers={"X-User-Id": user.id})
    assert resp.status_code == 200
    case = resp.json()
    assert case["title"] == "My Case"

    resp2 = client.get(f"/api/cases/{case['id']}", headers={"X-User-Id": user.id})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == case["id"]


def test_case_isolation_blocks_other_owner(client, make_user):
    owner = make_user(role="ADVOCATE")
    other = make_user(role="ADVOCATE")
    resp = client.post("/api/cases", json={"title": "Owner's Case"}, headers={"X-User-Id": owner.id})
    case_id = resp.json()["id"]

    resp2 = client.get(f"/api/cases/{case_id}", headers={"X-User-Id": other.id})
    assert resp2.status_code == 403


def test_admin_can_access_any_case(client, make_user):
    owner = make_user(role="ADVOCATE")
    admin = make_user(role="ADMIN")
    resp = client.post("/api/cases", json={"title": "Owner's Case"}, headers={"X-User-Id": owner.id})
    case_id = resp.json()["id"]

    resp2 = client.get(f"/api/cases/{case_id}", headers={"X-User-Id": admin.id})
    assert resp2.status_code == 200


def test_citizen_cannot_create_requirement(client, make_user):
    citizen = make_user(role="CITIZEN")
    resp = client.post("/api/cases", json={"title": "Citizen Case"}, headers={"X-User-Id": citizen.id})
    case_id = resp.json()["id"]
    pkg_resp = client.post(f"/api/cases/{case_id}/filing-packages", json={"name": "Pkg"},
                            headers={"X-User-Id": citizen.id})
    pkg_id = pkg_resp.json()["id"]

    req_resp = client.post(
        f"/api/filing-packages/{pkg_id}/requirements",
        json={"requirement_type": "DOCUMENT_REQUIRED", "description": "X required",
              "source": "USER_PROVIDED_CHECKLIST"},
        headers={"X-User-Id": citizen.id},
    )
    assert req_resp.status_code == 403


def test_create_filing_package(client, make_user):
    user = make_user(role="ADVOCATE")
    case_resp = client.post("/api/cases", json={"title": "C"}, headers={"X-User-Id": user.id})
    case_id = case_resp.json()["id"]
    pkg_resp = client.post(f"/api/cases/{case_id}/filing-packages", json={"name": "Initial Package"},
                            headers={"X-User-Id": user.id})
    assert pkg_resp.status_code == 200
    assert pkg_resp.json()["lifecycle_state"] == "DRAFT"


def test_list_filing_packages_respects_case_isolation(client, make_user):
    owner = make_user(role="ADVOCATE")
    other = make_user(role="ADVOCATE")
    case_resp = client.post("/api/cases", json={"title": "C"}, headers={"X-User-Id": owner.id})
    case_id = case_resp.json()["id"]
    client.post(f"/api/cases/{case_id}/filing-packages", json={"name": "Pkg"}, headers={"X-User-Id": owner.id})

    resp = client.get(f"/api/cases/{case_id}/filing-packages", headers={"X-User-Id": other.id})
    assert resp.status_code == 403
