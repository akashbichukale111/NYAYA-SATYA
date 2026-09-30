import io


def _setup_case_package(client, user):
    case_resp = client.post("/api/cases", json={"title": "Reasoning Test Case"}, headers={"X-User-Id": user.id})
    case_id = case_resp.json()["id"]
    pkg_resp = client.post(f"/api/cases/{case_id}/filing-packages", json={"name": "Pkg"},
                            headers={"X-User-Id": user.id})
    return case_id, pkg_resp.json()["id"]


def test_missing_attachment_reference_produces_defect(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, user)

    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition", "document_kind": "petition"},
        files={"file": ("petition.txt", io.BytesIO(
            b"The petitioner attaches identity proof as Annexure A and prior order as Annexure B."
        ), "text/plain")},
        headers={"X-User-Id": user.id},
    )
    # Annexure A IS uploaded; Annexure B is NOT.
    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Annexure A", "document_kind": "annexure"},
        files={"file": ("annexure_a.txt", io.BytesIO(b"Identity proof document."), "text/plain")},
        headers={"X-User-Id": user.id},
    )

    result = client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": user.id}).json()
    assert result["new_defect_count"] >= 1

    defects = client.get(f"/api/filing-packages/{pkg_id}/defects", headers={"X-User-Id": user.id}).json()
    types = {d["defect_type"] for d in defects}
    assert "MISSING_REFERENCED_ITEM" in types
    missing_defect = next(d for d in defects if d["defect_type"] == "MISSING_REFERENCED_ITEM")
    assert "Annexure B" in missing_defect["description"]
    # Never claims a legal consequence.
    assert "reject" not in missing_defect["description"].lower()
    assert "invalid" not in missing_defect["description"].lower()


def test_unknown_requirement_creates_human_review_defect(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, user)

    client.post(
        f"/api/filing-packages/{pkg_id}/requirements",
        json={
            "requirement_type": "DOCUMENT_REQUIRED",
            "description": "Something the system cannot verify the source of",
            "source": "UNKNOWN",
        },
        headers={"X-User-Id": user.id},
    )
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": user.id})
    checklist = client.get(f"/api/filing-packages/{pkg_id}/checklist", headers={"X-User-Id": user.id}).json()
    assert any(item["status"] == "REQUIRES_HUMAN_REVIEW" for item in checklist)


def test_review_approve_confirms_defect(client, make_user):
    advocate = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, advocate)

    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition"},
        files={"file": ("p.txt", io.BytesIO(b"References Annexure Z which is absent."), "text/plain")},
        headers={"X-User-Id": advocate.id},
    )
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": advocate.id})
    queue = client.get(f"/api/filing-packages/{pkg_id}/review-queue", headers={"X-User-Id": advocate.id}).json()
    assert len(queue) >= 1
    review_id = queue[0]["id"]

    resp = client.post(f"/api/reviews/{review_id}/approve", json={"reason": "Confirmed after manual check"},
                        headers={"X-User-Id": advocate.id})
    assert resp.status_code == 200
    assert resp.json()["decision"] == "APPROVED"

    defect = client.get(f"/api/defects/{queue[0]['target_id']}", headers={"X-User-Id": advocate.id}).json()
    assert defect["status"] == "CONFIRMED"


def test_review_reject_marks_defect_rejected(client, make_user):
    advocate = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, advocate)
    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition"},
        files={"file": ("p.txt", io.BytesIO(b"References Annexure Q which is absent."), "text/plain")},
        headers={"X-User-Id": advocate.id},
    )
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": advocate.id})
    queue = client.get(f"/api/filing-packages/{pkg_id}/review-queue", headers={"X-User-Id": advocate.id}).json()
    review_id = queue[0]["id"]

    resp = client.post(f"/api/reviews/{review_id}/reject", json={"reason": "False positive - not applicable"},
                        headers={"X-User-Id": advocate.id})
    assert resp.status_code == 200
    defect = client.get(f"/api/defects/{queue[0]['target_id']}", headers={"X-User-Id": advocate.id}).json()
    assert defect["status"] == "REJECTED"
    assert defect["human_review_required"] is False


def test_audit_trail_records_review_decision(client, make_user):
    advocate = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, advocate)
    client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition"},
        files={"file": ("p.txt", io.BytesIO(b"References Annexure R which is absent."), "text/plain")},
        headers={"X-User-Id": advocate.id},
    )
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": advocate.id})
    queue = client.get(f"/api/filing-packages/{pkg_id}/review-queue", headers={"X-User-Id": advocate.id}).json()
    client.post(f"/api/reviews/{queue[0]['id']}/approve", json={"reason": "ok"}, headers={"X-User-Id": advocate.id})

    audit = client.get(f"/api/filing-packages/{pkg_id}/audit", headers={"X-User-Id": advocate.id}).json()
    actions = {a["action"] for a in audit}
    assert "REVIEW_APPROVED" in actions
    assert "UPLOAD_DOCUMENT" in actions
    assert "RUN_PRECHECK" in actions


def test_objection_creates_linked_defect(client, make_user):
    advocate = make_user(role="ADVOCATE")
    case_id, pkg_id = _setup_case_package(client, advocate)
    client.post(f"/api/filing-packages/{pkg_id}/objections",
                json={"original_text": "Missing signature page.", "source_reference": "Registry letter dated X"},
                headers={"X-User-Id": advocate.id})
    client.post(f"/api/filing-packages/{pkg_id}/precheck", headers={"X-User-Id": advocate.id})

    defects = client.get(f"/api/filing-packages/{pkg_id}/defects", headers={"X-User-Id": advocate.id}).json()
    assert any(d["defect_type"] == "UNRESOLVED_OBJECTION" for d in defects)

    objections = client.get(f"/api/filing-packages/{pkg_id}/objections", headers={"X-User-Id": advocate.id}).json()
    assert objections[0]["linked_defect_id"] is not None
