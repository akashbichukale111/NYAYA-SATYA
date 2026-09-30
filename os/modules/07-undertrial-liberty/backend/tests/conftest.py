import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def test_db_path(tmp_path):
    return str(tmp_path / "test_uls.db")


@pytest.fixture()
def client(test_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db_path}")
    # Force a fresh import of the db/session module bound to this test's DB
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("app"):
            del sys.modules[mod_name]
    from app.main import app
    with TestClient(app) as c:
        yield c


ADVOCATE_HEADERS = {"X-Demo-Role": "ADVOCATE", "X-Demo-User": "test-advocate"}
CITIZEN_HEADERS = {"X-Demo-Role": "CITIZEN", "X-Demo-User": "test-citizen"}
ADMIN_HEADERS = {"X-Demo-Role": "ADMIN", "X-Demo-User": "test-admin"}


def create_case(client, headers=ADVOCATE_HEADERS, ref="TEST-001"):
    resp = client.post("/api/cases", json={
        "case_reference": ref, "title": "Test Case", "person_full_name": "Test Person",
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def upload_text_document(client, case_id, filename, text, headers=ADVOCATE_HEADERS):
    return client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": (filename, text.encode("utf-8"), "text/plain")},
        headers=headers,
    )
