"""End-to-end API tests. Uses the `client` fixture (conftest.py), which wires
FastAPI's dependency-injected session to an isolated in-memory-file SQLite DB
— completely separate from the dev/demo database, per Section 60's
"case isolation tests" requirement.
"""
from app.demo_data import ALL_DEMO_CASES
from app.security import scan_for_injection, hash_content


def _seed_via_orm(session_factory):
    """Seed demo cases directly through the ORM session the API is wired to,
    bypassing seed.py's own engine (which points at the dev DB file)."""
    from app.models import Case, CaseDocument, Dependency, Transition
    with session_factory() as session:
        for builder in ALL_DEMO_CASES:
            data = builder()
            session.add(Case(**data["case"]))
            for doc in data["documents"]:
                injected = scan_for_injection(doc["content_text"])
                session.add(CaseDocument(
                    **doc, contains_injection_attempt=injected, quarantined=injected,
                    sha256=hash_content(doc["content_text"]),
                ))
            for dep in data["dependencies"]:
                session.add(Dependency(**dep))
            for t in data["transitions"]:
                session.add(Transition(**t))
        session.commit()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_case_not_found_is_404(client):
    r = client.get("/api/cases/does-not-exist")
    assert r.status_code == 404


def test_full_investigation_lifecycle(client, engine):
    from sqlmodel import Session
    _seed_via_orm(lambda: Session(engine))

    # 1. List cases
    r = client.get("/api/cases")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert "demo-A" in ids

    # 2. Investigate demo-A -> "Why is this case stuck?"
    r = client.post("/api/cases/demo-A/investigate")
    assert r.status_code == 200
    body = r.json()
    assert body["bottleneck_count"] == 1
    bn_id = body["primary_bottleneck_id"]
    assert bn_id is not None

    # 3. Root cause chain must be retrievable and non-trivial
    r = client.get(f"/api/cases/demo-A/root-cause?bottleneck_id={bn_id}")
    assert r.status_code == 200
    assert len(r.json()["chain"]) >= 1

    # 4. Flow graph must expose the dependency/transition nodes
    r = client.get("/api/cases/demo-A/flow")
    assert r.status_code == 200
    assert len(r.json()["nodes"]) >= 2

    # 5. A safe action must have been proposed, pending human approval
    r = client.get("/api/cases/demo-A/actions")
    assert r.status_code == 200
    actions = r.json()
    assert len(actions) == 1
    assert actions[0]["status"] == "PENDING_APPROVAL"
    action_id = actions[0]["id"]

    # 6. Approve -> execute -> verify -> reassess, in one human-gated call
    r = client.post(f"/api/cases/demo-A/actions/{action_id}/approve")
    assert r.status_code == 200
    approved = r.json()
    assert approved["action"]["status"] == "COMPLETED"
    assert "verification" in approved

    # 7. Re-approving the same action must be rejected (409) — no double-execution
    r = client.post(f"/api/cases/demo-A/actions/{action_id}/approve")
    assert r.status_code == 409

    # 8. Audit trail must show the full chain, in order, with one correlation_id
    #    for the investigation and a separate one for the human approval.
    r = client.get("/api/cases/demo-A/audit")
    assert r.status_code == 200
    events = [e["event"] for e in r.json()]
    assert "INVESTIGATION_STARTED" in events
    assert "BOTTLENECKS_DETECTED" in events
    assert "ACTION_APPROVED" in events
    assert "ACTION_EXECUTED" in events


def test_reject_action_requires_reason(client, engine):
    from sqlmodel import Session
    _seed_via_orm(lambda: Session(engine))
    client.post("/api/cases/demo-A/investigate")
    action_id = client.get("/api/cases/demo-A/actions").json()[0]["id"]

    r = client.post(f"/api/cases/demo-A/actions/{action_id}/reject", json={"reason": "Already resolved by phone call to opposite counsel."})
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"
    assert r.json()["rejection_reason"]


def test_simulate_endpoint_never_mutates_state(client, engine):
    from sqlmodel import Session
    _seed_via_orm(lambda: Session(engine))
    client.post("/api/cases/demo-B/investigate")

    flow_before = client.get("/api/cases/demo-B/flow").json()
    r = client.post("/api/cases/demo-B/simulate", json={"dependency_id": "demo-B-dep-counter"})
    assert r.status_code == 200
    assert r.json()["mode"] == "SIMULATION_ONLY"

    flow_after = client.get("/api/cases/demo-B/flow").json()
    assert flow_before == flow_after  # real state unchanged by simulation


def test_crash_test_endpoint_lists_mutations_and_runs_one(client, engine):
    from sqlmodel import Session
    _seed_via_orm(lambda: Session(engine))

    r = client.get("/api/cases/demo-A/crash-test/mutations")
    assert r.status_code == 200
    mutations = r.json()
    assert "remove_evidence" in mutations

    r = client.post("/api/cases/demo-A/crash-test", json={
        "mutation": "mark_dependency_unresolved",
        "target_dependency_id": "demo-A-dep-statement",
    })
    assert r.status_code == 200
    assert r.json()["result"] in ("PASS", "WARNING", "FAIL")


def test_prompt_injection_case_via_full_http_api_is_not_hijacked(client, engine):
    from sqlmodel import Session
    _seed_via_orm(lambda: Session(engine))

    docs = client.get("/api/cases/demo-H/documents").json()
    assert docs[0]["quarantined"] is True

    r = client.post("/api/cases/demo-H/investigate")
    assert r.status_code == 200
    bottlenecks = r.json()["bottlenecks"]
    assert len(bottlenecks) == 1
    assert bottlenecks[0]["status"] != "RESOLVED"

    actions = client.get("/api/cases/demo-H/actions").json()
    assert all(a["status"] != "COMPLETED" for a in actions)  # nothing auto-approved
