"""
NYAYA-SATYA Platform UI & Integration Tests
Verifies the Global Legal Case Intelligence Platform frontend:
- Dedicated Workspaces & Single-Page Router
- Floating Action Button (✦ Personal AI) strict decoupling
- Non-adjudication guarantees
- Multi-jurisdiction & Citizen intake endpoints
- Multi-language dictionary
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO / "web" / "static" / "index.html"
STYLE_CSS = REPO / "web" / "static" / "style.css"
APP_JS = REPO / "web" / "static" / "app.js"


@pytest.fixture(scope="module")
def html_content() -> str:
    assert INDEX_HTML.is_file(), "web/static/index.html is missing"
    return INDEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js_content() -> str:
    assert APP_JS.is_file(), "web/static/app.js is missing"
    return APP_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def style_css_content() -> str:
    assert STYLE_CSS.is_file(), "web/static/style.css is missing"
    return STYLE_CSS.read_text(encoding="utf-8")


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("UNWIND_DEV_PRINCIPAL", "dev-test-jurist")
    from services.api.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Floating Action Button (✦ Personal AI) Strict Decoupling Tests
# ---------------------------------------------------------------------------


def test_personal_ai_fab_exists_in_html(html_content: str) -> None:
    """The floating action button must be present with the exact label and target."""
    assert 'id="personal-ai-fab-btn"' in html_content
    assert "✦ Personal AI" in html_content
    assert "https://frontend-henna-gamma-fhj87crlpp.vercel.app/" in html_content
    assert 'target="_blank"' in html_content
    assert 'rel="noopener noreferrer"' in html_content


def test_personal_ai_no_iframe_embedding(html_content: str) -> None:
    """Akash AI must NOT be embedded as an iframe inside the platform."""
    matches = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
    for src in matches:
        assert "vercel.app" not in src, f"Forbidden iframe embedding of external AI: {src}"


def test_personal_ai_fab_in_app_js(app_js_content: str) -> None:
    """app.js must strictly open the external URL in a new tab without passing case data."""
    assert "personal-ai-fab-btn" in app_js_content
    assert "https://frontend-henna-gamma-fhj87crlpp.vercel.app/" in app_js_content
    assert "_blank" in app_js_content
    assert "noopener,noreferrer" in app_js_content


def test_personal_ai_fab_in_style_css(style_css_content: str) -> None:
    """CSS must position the button at the bottom-right corner."""
    assert ".personal-ai-fab" in style_css_content
    assert "position: fixed;" in style_css_content
    assert "bottom: 24px;" in style_css_content
    assert "right: 24px;" in style_css_content


# ---------------------------------------------------------------------------
# 2. Dedicated Workspaces & Single-Page Router Tests
# ---------------------------------------------------------------------------


def test_router_workspaces_in_app_js(app_js_content: str) -> None:
    """The router must support all key platform workspaces."""
    expected_routes = [
        "home", "new-case", "my-cases", "evidence", "twin",
        "attack", "bottleneck", "deadlines", "impact", "counterfactual",
        "repair", "reattack", "governance", "dossier", "health",
        "citizen", "activity"
    ]
    for route in expected_routes:
        assert f"'{route}':" in app_js_content or f'"{route}":' in app_js_content, f"Missing route {route}"


def test_homepage_elements_in_html(html_content: str) -> None:
    """Homepage must feature the clean greeting, action cards, and system status."""
    assert "What do you want to do?" in html_content
    assert "New Case" in html_content
    assert "Evidence" in html_content
    assert "Case Digital Twin" in html_content
    assert "Attack Case" in html_content
    assert "Case Health" in html_content
    assert "Dossier" in html_content
    assert "Recent Cases" in html_content


def test_non_adjudication_compliance(html_content: str, app_js_content: str) -> None:
    """Outputs must strictly not predict verdicts, guilt, or win probabilities."""
    forbidden = ["win probability", "verdict predictor", "guilt score", "likelihood of victory"]
    for term in forbidden:
        assert term not in html_content.lower(), f"Non-adjudication violation in HTML: {term}"
        assert term not in app_js_content.lower(), f"Non-adjudication violation in app.js: {term}"


# ---------------------------------------------------------------------------
# 3. New API Platform Endpoints Tests
# ---------------------------------------------------------------------------


def test_api_jurisdictions(auth_client: TestClient) -> None:
    """GET /api/nyaya/jurisdictions must return supported statutory systems."""
    res = auth_client.get("/api/nyaya/jurisdictions")
    assert res.status_code == 200
    data = res.json()
    assert "jurisdictions" in data
    codes = [j["id"] for j in data["jurisdictions"]]
    assert any(c.startswith("IN") for c in codes)
    assert any(c.startswith("US") for c in codes)
    assert any(c.startswith("UK") for c in codes)
    assert any(c.startswith("SG") for c in codes)


def test_api_citizen_intake(auth_client: TestClient) -> None:
    """POST /api/nyaya/citizen/intake must structure plain-language citizen complaints."""
    payload = {
        "problem_statement": "I was evicted by my landlord without 30 days statutory notice.",
        "jurisdiction": "IN-MH-PUN",
        "language": "en"
    }
    res = auth_client.post("/api/nyaya/citizen/intake", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "plain_language_summary" in data or "problem_summary" in data
    assert "detected_category" in data or "issue_category" in data
    assert "required_documents" in data or "recommended_evidence_checklist" in data
    assert "legal_aid_referral" in data or "legal_aid" in data
    # Non-adjudication guarantee
    assert "verdict" not in data
    assert "win_probability" not in data


def test_api_case_bottlenecks(auth_client: TestClient) -> None:
    """GET /api/nyaya/cases/{case_id}/bottlenecks must return procedural delay factors."""
    res = auth_client.get("/api/nyaya/cases/CASE_SYNTHETIC_DEMO_2026/bottlenecks")
    assert res.status_code == 200
    data = res.json()
    assert "case_id" in data
    assert "bottlenecks" in data
    assert isinstance(data["bottlenecks"], list)


def test_api_case_triage(auth_client: TestClient) -> None:
    """GET /api/nyaya/cases/{case_id}/triage must return urgency categorization."""
    res = auth_client.get("/api/nyaya/cases/CASE_SYNTHETIC_DEMO_2026/triage")
    assert res.status_code == 200
    data = res.json()
    assert "case_id" in data
    assert "urgency" in data
    assert "priority_score" in data
