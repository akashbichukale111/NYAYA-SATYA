"""Master Platform Integration & 13 Experiences Test Suite.
Verifies:
1. Original NYAYA-SATYA Core Experience (/os/core)
2. Master OS Command Center (/os and /)
3. All 12 Specialized Intelligence Engines (/os/projects/{slug})
4. Shared CaseContext synchronization & cross-project navigation
5. Non-adjudication safety guarantees
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, r"D:\NYAYA-SATYA\os")
sys.path.insert(0, r"D:\NYAYA-SATYA\unwind-live-verified-main")

from gateway.main import app

client = TestClient(app)


def test_root_health():
    """Verify Master Platform health reporting 13 experiences."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["experiences_count"] == 13
    assert "ZERO_OUTCOME_PREDICTION" in data["non_adjudication_invariant"]


def test_system_health_report():
    """Verify system health reports Core + 12 Engines = 13 experiences."""
    res = client.get("/system-health")
    assert res.status_code == 200
    data = res.json()
    assert data["total_experiences"] == 13
    assert data["core_status"]["name"] == "NYAYA-SATYA CORE"
    assert len(data["engines"]) == 12


def test_experience_00_core_nyaya_satya():
    """Verify Experience 0: Original NYAYA-SATYA Core UI and injected OS return header."""
    res = client.get("/os/core")
    assert res.status_code == 200
    html = res.text
    assert "NYAYA-SATYA" in html
    assert "Back to NYAYA-SATYA OS" in html
    assert "os-master-header" in html


def test_experience_master_os_command_center():
    """Verify Master OS Command Center Shell loads with permanent sidebar."""
    res = client.get("/os")
    assert res.status_code == 200
    html = res.text
    assert "NYAYA-SATYA CORE" in html
    assert "INTELLIGENCE ENGINES" in html
    assert "Command Center" in html
    assert "13 Experiences Online" in html


# ---------------------------------------------------------------------------
# Test All 12 Specialized Project Experiences
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug,expected_title", [
    ("hearing-readiness", "Hearing Readiness Engine"),
    ("case-continuity", "Case Continuity Engine"),
    ("case-bottleneck", "Case Bottleneck Engine"),
    ("legal-aid-handoff", "Legal-Aid Handoff Engine"),
    ("procedural-obligation", "Procedural Obligation Engine"),
    ("evidence-dependency", "Evidence Dependency Engine"),
    ("undertrial-liberty", "Undertrial Liberty Sentinel"),
    ("registry-defect", "Registry Defect Engine"),
    ("case-crash-test", "Case Crash Test Lab"),
    ("spark-personal-os", "Spark Personal OS"),
    ("spark-deadline-guardian", "Spark Deadline Guardian"),
    ("spark-workflow-autopilot", "Spark Workflow Autopilot"),
])
def test_all_12_specialized_project_pages(slug, expected_title):
    res = client.get(f"/os/projects/{slug}")
    assert res.status_code == 200
    html = res.text
    assert expected_title in html
    assert "Back to NYAYA-SATYA OS" in html
    assert "CASE CONTEXT:" in html


def test_shared_case_context_switching():
    """Verify switching case updates active context globally across Core & Engines."""
    # 1. Switch to Commercial Case
    res_switch = client.post("/api/cases/switch?case_id=CASE-2023-BOM-1109")
    assert res_switch.status_code == 200
    assert res_switch.json()["active_case"]["case_id"] == "CASE-2023-BOM-1109"

    # 2. Verify Cockpit summary reflects this case
    res_cockpit = client.get("/api/cockpit/summary")
    assert res_cockpit.status_code == 200
    data = res_cockpit.json()
    assert data["active_case"]["case_id"] == "CASE-2023-BOM-1109"

    # 3. Switch back to Undertrial Case
    client.post("/api/cases/switch?case_id=CASE-2024-DEL-0482")


def test_unwind_human_gate():
    """Verify UNWIND Human Legal Gate signoff on active case."""
    res = client.post("/api/cases/CASE-2024-DEL-0482/authorize?approver=Adv.+Meenakshi+Sundaram")
    assert res.status_code == 200
    assert res.json()["status"] == "AUTHORIZED"


def test_cross_project_search():
    """Verify search finds Core, Cases, and Specialized Engines."""
    res = client.get("/api/search?q=core")
    assert res.status_code == 200
    data = res.json()
    assert any(r["title"] == "NYAYA-SATYA CORE" for r in data["results"])

    res_lib = client.get("/api/search?q=liberty")
    assert res_lib.status_code == 200
    assert any("Undertrial Liberty" in r["title"] for r in res_lib.json()["results"])
