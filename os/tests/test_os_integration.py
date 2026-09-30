"""Comprehensive Integration & Safety Test Suite for NYAYA-SATYA OS.
Verifies all 12 engines, case context propagation, UNWIND human gate,
global search, and non-adjudication safety invariants.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure D:\NYAYA-SATYA is in python path
sys.path.insert(0, r"D:\NYAYA-SATYA")

from gateway.main import app
from contracts.models import ModuleHealthStatus

client = TestClient(app)


def test_root_health():
    """Verify core OS health endpoint and safety invariants."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["system"] == "NYAYA-SATYA OS"
    assert data["engines_mounted"] == 12
    assert "ZERO_OUTCOME_PREDICTION" in data["non_adjudication_invariant"]


def test_system_health_all_12_engines():
    """Verify system diagnostics reports all 12 engines with correct status."""
    res = client.get("/system-health")
    assert res.status_code == 200
    data = res.json()
    assert data["total_engines"] == 12
    assert len(data["modules"]) == 12
    
    # Verify Project 05 is correctly flagged as PARTIAL / SECTION 1 PRESENT
    mod_05 = next(m for m in data["modules"] if m["number"] == 5)
    assert mod_05["status"] == "PARTIAL"
    assert "SECTION 1" in mod_05["notes"]
    
    # Verify non-adjudication audit passed
    assert "PASSED" in data["safety_invariants"]["non_adjudicative_audit"]
    assert "ENFORCED" in data["safety_invariants"]["unwind_human_gate"]


def test_case_context_and_switching():
    """Verify case context retrieval and switching across multi-tenant cases."""
    # Check default active case
    res = client.get("/api/cases/active")
    assert res.status_code == 200
    active = res.json()
    assert active["case_id"] == "CASE-2024-DEL-0482"
    
    # Switch to Commercial Case
    res_switch = client.post("/api/cases/switch?case_id=CASE-2023-BOM-1109")
    assert res_switch.status_code == 200
    assert res_switch.json()["active_case"]["jurisdiction"] == "COMMERCIAL"
    
    # Switch back
    client.post("/api/cases/switch?case_id=CASE-2024-DEL-0482")


def test_unwind_human_gate_authorization():
    """Verify UNWIND human gate authorization flow."""
    res = client.post("/api/cases/CASE-2024-DEL-0482/authorize?approver=Adv.+Meenakshi+Sundaram")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AUTHORIZED"
    assert data["case"]["human_authorized"] is True


def test_cockpit_consolidated_summary():
    """Verify /api/cockpit/summary delivers unified metrics for all 12 engines."""
    res = client.get("/api/cockpit/summary?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    data = res.json()
    assert len(data["modules"]) == 12
    assert "active_case" in data
    assert "attention_items" in data
    
    # Check Undertrial Sentinel summary in cockpit
    mod_07 = next(m for m in data["modules"] if m["number"] == 7)
    assert "days_in_custody" in mod_07["summary"]
    assert mod_07["summary"]["days_in_custody"] == 418


def test_global_search():
    """Verify Ctrl+K global search queries across cases and engines."""
    res = client.get("/api/search?q=bail")
    assert res.status_code == 200
    data = res.json()
    assert data["total_matches"] > 0
    matches = [r["title"] for r in data["results"]]
    assert any("Bail" in m or "Undertrial" in m or "Rajesh" in m for m in matches)


def test_procedural_obligation_engine():
    """Verify Module 05 WHO/WHAT/LOSS/SIGN compliance."""
    res = client.get("/api/modules/procedural-obligation/obligations?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    obs = res.json()
    assert len(obs) >= 1
    ob = obs[0]
    assert "counterparties" in ob
    assert "reversible_actions" in ob
    assert "irreversible_loss" in ob
    assert ob["status"] == "AWAITING_AUTHORISATION"


def test_undertrial_liberty_sentinel():
    """Verify Module 07 Section 479 BNSS / 436A CrPC liberty calculation."""
    res = client.get("/api/modules/undertrial-liberty/audit?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    audit = res.json()
    assert audit["days_in_custody"] == 418
    assert audit["statutory_threshold_1_3"] == 365
    assert audit["eligible_under_bnss_479"] is True
    assert audit["threshold_surpassed_by_days"] == 53


def test_evidence_dependency_engine():
    """Verify Module 06 Evidence DAG and single-point-of-failure analysis."""
    res = client.get("/api/modules/evidence-dependency/graph?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    graph = res.json()
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
    assert "C3 (Chain of Custody)" in graph["single_points_of_failure"]


def test_registry_defect_engine():
    """Verify Module 08 Scrutiny Defect audit."""
    res = client.get("/api/modules/registry-defect/defects?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    data = res.json()
    assert data["total_defects"] >= 2
    assert "cure_deadline" in data


def test_spark_deadline_guardian():
    """Verify Module 11 Limitation Act statutory countdowns."""
    res = client.get("/api/modules/spark-deadline-guardian/deadlines?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    data = res.json()
    assert len(data["statutory_calendar"]) >= 2


def test_spark_workflow_autopilot():
    """Verify Module 12 procedural SOP runner and human gate."""
    res = client.get("/api/modules/spark-workflow-autopilot/workflows?case_id=CASE-2024-DEL-0482")
    assert res.status_code == 200
    data = res.json()
    assert len(data["workflows"]) >= 1
    assert data["workflows"][0]["human_gate_active"] is True
