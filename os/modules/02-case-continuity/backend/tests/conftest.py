import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Fresh SQLite file DB + fresh upload dir per test, via TestClient's
    startup lifecycle (init_db runs on app startup).
    """
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    # Reload config/database/app fresh so env vars above take effect,
    # since app.config.settings is built at import time.
    for mod_name in list(sys.modules):
        if mod_name == "app" or mod_name.startswith("app."):
            del sys.modules[mod_name]

    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app

    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture()
def seeded_client(client):
    r = client.post("/api/demo/seed")
    assert r.status_code == 200
    return client


def get_case_by_key(client, key: str) -> dict:
    r = client.get("/api/cases")
    for c in r.json():
        if c["demo_case_key"] == key:
            return c
    raise AssertionError(f"demo case {key} not found")
