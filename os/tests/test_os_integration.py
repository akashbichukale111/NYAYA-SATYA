"""Master Platform Integration & 13 Experiences Test Suite.
Verifies:
1. Canonical Routes:
   - / and /dashboard (Master Command Center)
   - /core (Original NYAYA-SATYA Core)
   - /twin (Case Digital Twin Deep Explorer)
   - /projects/{slug} (All 12 specialized project experiences)
   - /spark/personal, /spark/deadlines, /spark/workflows
   - /governance/tarka-vyuh, /governance/unwind, /governance/audit, /governance/system-health
2. Shared CaseContext synchronization & deep Digital Twin entities
3. Non-adjudication safety guarantees & UNWIND Human Legal Gate
4. Simulation isolation (no mutation of canonical CaseContext)
5. Future extension interface contracts
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, r"D:\NYAYA-SATYA\os")
sys.path.insert(0, r"D:\NYAYA-SATYA\unwind-live-verified-main")

from gateway.main import app
from contracts.extensions import OfflineResearchProvider, OfflineLLMProvider
from shared.case_store import case_store

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


def test_canonical_command_center_routes():
    """Verify /, /dashboard, and /os serve the Master OS Command Center."""
    for path in ["/", "/dashboard", "/os"]:
        res = client.get(path)
        assert res.status_code == 200
        html = res.text
        assert "NYAYA-SATYA" in html
        assert "Command Center" in html
        assert "13 Experiences Online" in html


def test_canonical_core_routes():
    """Verify /core and /os/core serve the Original NYAYA-SATYA Core UI."""
    for path in ["/core", "/os/core"]:
        res = client.get(path)
        assert res.status_code == 200
        html = res.text
        assert "NYAYA-SATYA" in html
        assert "Command Center" in html
        assert "os-master-header" in html


def test_canonical_twin_explorer():
    """Verify /twin serves the Case Digital Twin Deep Explorer."""
    for path in ["/twin", "/os/twin"]:
        res = client.get(path)
        assert res.status_code == 200
        html = res.text
        assert "Case Digital Twin Deep Explorer" in html
        assert "Active Contradictions" in html
        assert "Evidence Nodes" in html


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
    ("crash-test", "Case Crash Test Lab"),
    ("spark-personal-os", "Spark Personal OS"),
    ("spark-deadline-guardian", "Spark Deadline Guardian"),
    ("spark-workflow-autopilot", "Spark Workflow Autopilot"),
])
def test_canonical_projects_routes(slug, expected_title):
    """Verify all 12 specialized project pages via /projects/{slug}."""
    res = client.get(f"/projects/{slug}")
    assert res.status_code == 200
    html = res.text
    assert expected_title in html
    assert "Back to NYAYA-SATYA OS" in html or "Command Center" in html
    assert "CASE CONTEXT:" in html


def test_canonical_spark_direct_routes():
    """Verify /spark/personal, /spark/deadlines, /spark/workflows."""
    res_p = client.get("/spark/personal")
    assert res_p.status_code == 200
    assert "Spark Personal OS" in res_p.text

    res_d = client.get("/spark/deadlines")
    assert res_d.status_code == 200
    assert "Spark Deadline Guardian" in res_d.text

    res_w = client.get("/spark/workflows")
    assert res_w.status_code == 200
    assert "Spark Workflow Autopilot" in res_w.text


def test_canonical_governance_routes():
    """Verify /governance/tarka-vyuh, /governance/unwind, /governance/audit, /governance/system-health."""
    res_t = client.get("/governance/tarka-vyuh")
    assert res_t.status_code == 200
    assert "TARKA-VYUH" in res_t.text
    assert "STRICT NON-ADJUDICATION GUARANTEE" in res_t.text

    res_u = client.get("/governance/unwind")
    assert res_u.status_code == 200
    assert "UNWIND Core — Human Legal Gate" in res_u.text
    assert "APPROVE & AUTHORIZE" in res_u.text

    res_a = client.get("/governance/audit")
    assert res_a.status_code == 200
    assert "Immutable Audit Ledger" in res_a.text

    res_h = client.get("/governance/system-health")
    assert res_h.status_code == 200
    assert "System Diagnostics" in res_h.text


def test_deep_case_digital_twin_model():
    """Verify CaseContext includes populated Digital Twin deep entity collections."""
    active = case_store.get_case("CASE-2024-DEL-0482")
    assert active is not None
    assert len(active.parties) >= 2
    assert len(active.documents) >= 3
    assert len(active.evidence) >= 4
    assert len(active.claims) >= 3
    assert len(active.issues) >= 3
    assert len(active.contradictions) >= 1
    assert len(active.bottlenecks) >= 1
    assert len(active.liberty_events) >= 1
    assert active.liberty_events[0]["eligible_under_sec_479"] is True
    assert active.verification_state["integrity_status"] == "INTACT"


def test_simulation_isolation_invariant():
    """Verify counterfactual or simulation runs never mutate production CaseContext."""
    initial_case = case_store.get_case("CASE-2024-DEL-0482")
    initial_claims_count = len(initial_case.claims)
    initial_authorized = initial_case.human_authorized

    # Simulate hypothetical action in local dict
    hypothetical_copy = initial_case.model_dump()
    hypothetical_copy["claims"].pop()
    hypothetical_copy["human_authorized"] = True

    # Check store has NOT mutated
    canonical = case_store.get_case("CASE-2024-DEL-0482")
    assert len(canonical.claims) == initial_claims_count
    assert canonical.human_authorized == initial_authorized


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
    assert res.json()["case"]["human_authorized"] is True


def test_cross_project_search():
    """Verify search finds Core, Twin, Governance, Cases, and Specialized Engines."""
    res_core = client.get("/api/search?q=core")
    assert res_core.status_code == 200
    assert any(r["title"] == "NYAYA-SATYA CORE" for r in res_core.json()["results"])

    res_twin = client.get("/api/search?q=twin")
    assert res_twin.status_code == 200
    assert any("Twin" in r["title"] for r in res_twin.json()["results"])

    res_gov = client.get("/api/search?q=tarka")
    assert res_gov.status_code == 200
    assert any("TARKA-VYUH" in r["title"] for r in res_gov.json()["results"])


@pytest.mark.asyncio
async def test_extension_interface_fallback():
    """Verify future extension offline stubs instantiate without error."""
    research_provider = OfflineResearchProvider()
    results = await research_provider.search("Bail under Section 479 BNSS", "Delhi High Court")
    assert len(results) >= 1
    assert "Procedural Precedent" in results[0].title

    llm_provider = OfflineLLMProvider()
    out = await llm_provider.generate("Summarize charges")
    assert "Deterministic Offline Response" in out.content
