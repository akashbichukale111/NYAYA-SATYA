"""Test suite for Procedural Obligation Engine."""

from fastapi.testclient import TestClient
from os.modules.05-procedural-obligation.backend.app.main import app, OBLIGATIONS_DB
import pytest

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "SECTION 1" in data["status_note"]

def test_list_obligations_for_case():
    res = client.get("/api/cases/CASE-2024-DEL-0482/obligations")
    assert res.status_code == 200
    obs = res.json()
    assert len(obs) >= 1
    assert obs[0]["obligation_id"] == "OBL-2024-001"

def test_human_sign_obligation():
    res = client.post("/api/obligations/OBL-2024-001/sign", json={
        "approver_name": "Adv. Meenakshi Sundaram",
        "bar_council_id": "D/1492/2012"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AUTHORISED"
    assert "Meenakshi Sundaram" in data["approver"]

def test_render_obligation_memo():
    res = client.get("/api/obligations/OBL-2024-001/render")
    assert res.status_code == 200
    text = res.json()["text"]
    assert "WHO WAS TOLD" in text
    assert "REVERSIBLE ACTIONS" in text
    assert "IRREVERSIBLE EXPOSURE" in text
