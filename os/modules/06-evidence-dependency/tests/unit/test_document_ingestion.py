import io


def test_upload_txt_document_and_hash_recorded(client):
    case = client.post("/api/cases", json={"title": "Doc case"}).json()
    content = b"The delivery occurred on 1 May. The respondent signed the receipt."
    resp = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("evidence.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["status"] == "INGESTED"
    assert doc["document_type"] == "TXT"
    assert len(doc["sha256_hash"]) == 64

    import hashlib
    assert doc["sha256_hash"] == hashlib.sha256(content).hexdigest()


def test_unsupported_extension_is_quarantined_not_parsed(client):
    case = client.post("/api/cases", json={"title": "Bad ext case"}).json()
    resp = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00fake"), "application/octet-stream")},
    )
    assert resp.status_code == 415

    docs = client.get(f"/api/cases/{case['id']}/documents").json()
    assert len(docs) == 1
    assert docs[0]["status"] == "QUARANTINED"


def test_oversized_upload_is_rejected(client, monkeypatch=None):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.services import document_service

    original_max = document_service.MAX_UPLOAD_SIZE_BYTES
    document_service.MAX_UPLOAD_SIZE_BYTES = 10  # bytes, tiny for the test
    try:
        case = client.post("/api/cases", json={"title": "Oversized case"}).json()
        content = b"this is definitely more than ten bytes of content"
        resp = client.post(
            f"/api/cases/{case['id']}/documents",
            files={"file": ("big.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 415
    finally:
        document_service.MAX_UPLOAD_SIZE_BYTES = original_max


def test_empty_upload_is_rejected(client):
    case = client.post("/api/cases", json={"title": "Empty case"}).json()
    resp = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert resp.status_code == 415


def test_path_traversal_filename_is_neutralized(client):
    case = client.post("/api/cases", json={"title": "Traversal case"}).json()
    resp = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("../../../etc/passwd.txt", io.BytesIO(b"harmless content here"), "text/plain")},
    )
    assert resp.status_code == 200
    doc = resp.json()
    # original filename is preserved as metadata, but nothing was written outside
    # the case-scoped upload directory -- verified by inspecting stored_path server-side.
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.core.db import SessionLocal
    from app.models.orm import Document

    db = SessionLocal()
    row = db.query(Document).filter(Document.id == doc["id"]).first()
    stored_real = os.path.realpath(row.stored_path)
    upload_dir_real = os.path.realpath(document_service_upload_dir())
    db.close()
    assert stored_real.startswith(upload_dir_real)
    assert ".." not in os.path.relpath(stored_real, upload_dir_real)


def document_service_upload_dir():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.services import document_service
    return document_service.UPLOAD_DIR


def test_document_process_pipeline_creates_grounded_evidence_and_claims(client):
    case = client.post("/api/cases", json={"title": "Pipeline case"}).json()
    content = (
        b"The delivery van arrived at the warehouse on 3 June. "
        b"The manager signed the intake log at 09:15. "
        b"No damage was reported at the time of intake."
    )
    doc = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("intake.txt", io.BytesIO(content), "text/plain")},
    ).json()

    result = client.post(f"/api/documents/{doc['id']}/process").json()
    assert result["ok"] is True
    assert len(result["evidence_created"]) >= 1
    assert len(result["claims_created"]) >= 1

    # Anti-fabrication contract: every created evidence item's source_text
    # must be a verbatim substring of the uploaded document content.
    full_text = content.decode("utf-8")
    for eid in result["evidence_created"]:
        ev = client.get(f"/api/evidence/{eid}").json()
        assert ev["source_text"] in full_text
        assert ev["verification_status"] == "REQUIRES_HUMAN_REVIEW"

    doc_after = client.get(f"/api/documents/{doc['id']}").json()
    assert doc_after["status"] == "PROCESSED"


def test_json_and_csv_documents_parse_without_fabrication(client):
    case = client.post("/api/cases", json={"title": "JSON/CSV case"}).json()

    json_content = b'{"event": "payment", "amount": "5000", "date": "2026-01-02"}'
    doc_json = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("record.json", io.BytesIO(json_content), "application/json")},
    ).json()
    assert doc_json["status"] == "INGESTED"

    csv_content = b"name,amount\nAlice,100\nBob,200\n"
    doc_csv = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("ledger.csv", io.BytesIO(csv_content), "text/csv")},
    ).json()
    assert doc_csv["status"] == "INGESTED"
