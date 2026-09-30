import io


def _make_case_and_package(client, user):
    case_resp = client.post("/api/cases", json={"title": "C"}, headers={"X-User-Id": user.id})
    case_id = case_resp.json()["id"]
    pkg_resp = client.post(f"/api/cases/{case_id}/filing-packages", json={"name": "Pkg"},
                            headers={"X-User-Id": user.id})
    return case_id, pkg_resp.json()["id"]


def test_upload_txt_document_succeeds(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _make_case_and_package(client, user)

    resp = client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Petition", "document_kind": "petition"},
        files={"file": ("petition.txt", io.BytesIO(b"This is the petition text."), "text/plain")},
        headers={"X-User-Id": user.id},
    )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["display_name"] == "Petition"
    assert doc["current_version_id"] is not None


def test_upload_dangerous_extension_rejected(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _make_case_and_package(client, user)

    resp = client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Malicious"},
        files={"file": ("script.exe", io.BytesIO(b"MZ\x90\x00fakeexe"), "application/octet-stream")},
        headers={"X-User-Id": user.id},
    )
    assert resp.status_code == 400


def test_upload_empty_file_recorded_as_defect_worthy_but_not_crashing(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _make_case_and_package(client, user)

    resp = client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Empty Doc"},
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers={"X-User-Id": user.id},
    )
    assert resp.status_code == 200  # upload succeeds; quality issue is data, not a crash

    versions_resp = client.get(f"/api/documents/{resp.json()['id']}/versions", headers={"X-User-Id": user.id})
    version = versions_resp.json()[0]
    assert version["extraction_status"] == "FAILED"
    assert version["extraction_error"] == "EMPTY_DOCUMENT"


def test_upload_computes_sha256(client, make_user):
    user = make_user(role="ADVOCATE")
    case_id, pkg_id = _make_case_and_package(client, user)
    resp = client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Doc"},
        files={"file": ("doc.txt", io.BytesIO(b"hash me please"), "text/plain")},
        headers={"X-User-Id": user.id},
    )
    doc_id = resp.json()["id"]
    versions = client.get(f"/api/documents/{doc_id}/versions", headers={"X-User-Id": user.id}).json()
    assert versions[0]["sha256"] is not None and len(versions[0]["sha256"]) == 64


def test_document_upload_forbidden_across_case_isolation(client, make_user):
    owner = make_user(role="ADVOCATE")
    other = make_user(role="ADVOCATE")
    case_id, pkg_id = _make_case_and_package(client, owner)

    resp = client.post(
        f"/api/filing-packages/{pkg_id}/documents",
        data={"display_name": "Intrusion"},
        files={"file": ("doc.txt", io.BytesIO(b"content"), "text/plain")},
        headers={"X-User-Id": other.id},
    )
    assert resp.status_code == 403
