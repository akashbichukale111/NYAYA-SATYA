def _headers(user_id, role):
    return {"X-User-Id": user_id, "X-User-Role": role}


def test_no_auth_headers_default_to_admin_backward_compat(client):
    """No headers -> ADMIN/system-user, so the original 19 Section-1 tests
    (which send no auth headers) keep working unmodified."""
    resp = client.post("/api/cases", json={"title": "No headers case"})
    assert resp.status_code == 200


def test_unknown_role_header_rejected(client):
    resp = client.post("/api/cases", json={"title": "x"}, headers=_headers("u1", "SUPERUSER"))
    assert resp.status_code == 400


def test_citizen_cannot_access_another_users_private_case(client):
    owner_headers = _headers("owner-1", "ADVOCATE")
    stranger_headers = _headers("stranger-1", "CITIZEN")

    case = client.post("/api/cases", json={"title": "Private case"}, headers=owner_headers).json()

    # Stranger cannot read the case at all.
    resp = client.get(f"/api/cases/{case['id']}", headers=stranger_headers)
    assert resp.status_code == 403

    resp = client.get(f"/api/cases/{case['id']}/evidence", headers=stranger_headers)
    assert resp.status_code == 403


def test_owner_can_access_own_case(client):
    owner_headers = _headers("owner-2", "LEGAL_AID")
    case = client.post("/api/cases", json={"title": "Owned case"}, headers=owner_headers).json()
    resp = client.get(f"/api/cases/{case['id']}", headers=owner_headers)
    assert resp.status_code == 200


def test_admin_can_access_any_case(client):
    owner_headers = _headers("owner-3", "ADVOCATE")
    admin_headers = _headers("root-admin", "ADMIN")
    case = client.post("/api/cases", json={"title": "Owned case 2"}, headers=owner_headers).json()
    resp = client.get(f"/api/cases/{case['id']}", headers=admin_headers)
    assert resp.status_code == 200


def test_demo_cases_are_open_to_all_roles(client):
    case = client.post("/api/cases/demo/seed/A", json={}).json()
    citizen_headers = _headers("any-citizen", "CITIZEN")
    resp = client.get(f"/api/cases/{case['id']}", headers=citizen_headers)
    assert resp.status_code == 200


def test_citizen_cannot_approve_review_task(client):
    owner_headers = _headers("owner-4", "ADVOCATE")
    case = client.post("/api/cases", json={"title": "Review RBAC case"}, headers=owner_headers).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc"}, headers=owner_headers).json()

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.core.db import SessionLocal
    from app.services.review_service import propose_action

    db = SessionLocal()
    task = propose_action(
        db, case["id"], action_type="CHANGE_VERIFIED_STATUS", target_type="EVIDENCE",
        target_id=ev["id"], proposed_change={"verification_status": "VERIFIED"},
        proposing_agent="TestAgent",
    )
    db.close()

    citizen_headers = _headers("owner-4", "CITIZEN")  # same user id, lower role
    resp = client.post(f"/api/reviews/{task.id}/approve", json={"note": "try"}, headers=citizen_headers)
    assert resp.status_code == 403

    advocate_headers = owner_headers
    resp = client.post(f"/api/reviews/{task.id}/approve", json={"note": "ok"}, headers=advocate_headers)
    assert resp.status_code == 200
