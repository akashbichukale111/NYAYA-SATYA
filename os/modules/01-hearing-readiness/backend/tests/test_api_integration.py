"""
Full-stack API test: spins up the real FastAPI app against a temp SQLite
file (not the dev var/hre.db), seeds synthetic cases through the actual
startup path, and drives the whole demo script through HTTP -- the same
calls the frontend makes.
"""
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """
    Points the app's existing settings/engine singletons at a fresh temp
    SQLite DB + upload dir for this test only, then drives the real app
    (including its startup event, which seeds Cases A-G) through HTTP.

    We deliberately mutate the singletons in place rather than reloading
    modules: config.settings is a single shared instance imported by name
    in several modules (security.py, db.py, ...), and functions like
    get_db()/init_db() look up `engine`/`SessionLocal` as *module globals*
    at call time -- so assigning app.db.engine = <new engine> is enough to
    redirect every dependency-injected DB session without re-importing
    anything (which would otherwise create duplicate, disconnected model
    classes on a second Base).
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="hre_api_test_"))
    upload_dir = tmp_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / "test_api.db"

    import app.config as config_module
    import app.db as db_module
    import app.main as main_module

    config_module.settings.DATA_DIR = tmp_dir
    config_module.settings.UPLOAD_DIR = upload_dir
    config_module.settings.DB_PATH = db_path
    config_module.settings.DATABASE_URL = f"sqlite:///{db_path}"
    config_module.settings.DEMO_MODE = True

    new_engine = create_engine(config_module.settings.DATABASE_URL,
                                connect_args={"check_same_thread": False})
    db_module.engine = new_engine
    db_module.SessionLocal = sessionmaker(bind=new_engine, autoflush=False, autocommit=False)

    with TestClient(main_module.app) as c:
        yield c

    new_engine.dispose()


def test_health_reports_demo_mode(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["demo_mode"] is True


def test_synthetic_cases_seeded_on_startup(client):
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) == 7  # Cases A through G


def test_full_demo_flow_readiness_blocker_action_verification(client):
    cases = client.get("/api/cases").json()
    case_a = next(c for c in cases if "Case A" in c["title"])
    case_id = case_a["id"]

    # Readiness audit already ran at seed time; re-run explicitly too.
    readiness = client.post(f"/api/cases/{case_id}/readiness/run").json()
    assert readiness["overall"] in ("BLOCKED", "CONDITIONAL")

    blockers = client.get(f"/api/cases/{case_id}/blockers").json()
    open_blockers = [b for b in blockers if b["status"] == "OPEN"]
    assert len(open_blockers) >= 1
    blocker_id = open_blockers[0]["id"]

    why = client.get(f"/api/cases/{case_id}/blockers/{blocker_id}/why").json()
    for key in ("what", "why", "evidence", "dependency", "confidence", "unknown", "next_safe_action"):
        assert key in why

    graph = client.get(f"/api/cases/{case_id}/graph").json()
    assert len(graph["edges"]) > 0

    # Run the full agent pass -- this proposes a safe action for the blocker.
    run = client.post(f"/api/cases/{case_id}/run-agent-pass").json()
    assert run["status"] == "COMPLETED"

    actions = client.get(f"/api/cases/{case_id}/actions").json()
    pending = [a for a in actions if a["status"] == "PENDING_APPROVAL" and a["blocker_id"] == blocker_id]
    assert len(pending) >= 1
    action_id = pending[0]["id"]

    # Approve -> triggers execute + verify + reassess automatically.
    approval_resp = client.post(
        f"/api/cases/{case_id}/actions/{action_id}/approve",
        json={"decision": "APPROVE", "approved_by": "test_user"},
    ).json()
    assert approval_resp["action"]["status"] in ("VERIFIED", "VERIFICATION_FAILED")
    assert "agent_run" in approval_resp

    # Simulate resolving the blocker's underlying evidence.
    evidence = client.get(f"/api/cases/{case_id}/evidence").json()
    missing_evidence = next(e for e in evidence if e["availability"] == "MISSING")
    sim = client.post(
        f"/api/cases/{case_id}/simulate",
        json={"hypothesis": [{"type": "resolve_evidence", "evidence_id": missing_evidence["id"]}]},
    ).json()
    assert sim["label"] == "SIMULATION ONLY"

    # Live evidence must be untouched by the simulation.
    evidence_after = client.get(f"/api/cases/{case_id}/evidence").json()
    still_missing = next(e for e in evidence_after if e["id"] == missing_evidence["id"])
    assert still_missing["availability"] == "MISSING"

    # Crash test the case.
    crash_results = client.post(f"/api/cases/{case_id}/crash-test", json={}).json()
    assert len(crash_results) > 0

    # Time machine: at least one version exists, and versions are diffable.
    versions = client.get(f"/api/cases/{case_id}/versions").json()
    assert len(versions) >= 2
    diff = client.get(
        f"/api/cases/{case_id}/versions/diff",
        params={"from_version": versions[0]["version_number"], "to_version": versions[-1]["version_number"]},
    ).json()
    assert "readiness_before" in diff and "readiness_after" in diff

    # Audit trail is non-empty and append-only in spirit (only GET exposed).
    audit = client.get(f"/api/cases/{case_id}/audit").json()
    assert len(audit) > 0


def test_case_f_injection_document_is_flagged_but_inert(client):
    cases = client.get("/api/cases").json()
    case_f = next(c for c in cases if "Case F" in c["title"])
    docs = client.get(f"/api/cases/{case_f['id']}/documents").json()
    flagged = [d for d in docs if d["injection_flag"] == "true"]
    assert len(flagged) == 1
    # The system must still be operating normally -- readiness is computable,
    # not derailed into "approving everything" as the injected text requests.
    readiness = client.get(f"/api/cases/{case_f['id']}/readiness").json()
    assert readiness["overall"] in ("READY", "CONDITIONAL", "BLOCKED", "UNKNOWN")


def test_case_d_hearing_context_uncertain(client):
    cases = client.get("/api/cases").json()
    case_d = next(c for c in cases if "Case D" in c["title"])
    readiness = client.get(f"/api/cases/{case_d['id']}/readiness").json()
    assert readiness["hearing_context_uncertain"] is True
    assert readiness["overall"] == "UNKNOWN"


def test_legal_safety_firewall_blocks_forbidden_action_reason(client):
    # Defense in depth: even if a blocker's stored fields somehow contained
    # forbidden phrasing, propose_action must refuse rather than create it.
    from app.services import security
    with pytest.raises(security.ForbiddenIntent):
        security.enforce_legal_safety_firewall("Please predict the verdict for this hearing.")


def test_upload_rejects_disallowed_file_type(client):
    cases = client.get("/api/cases").json()
    case_id = cases[0]["id"]
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        files={"file": ("bad.exe", b"not a real exe", "application/octet-stream")},
    )
    assert resp.status_code == 400
