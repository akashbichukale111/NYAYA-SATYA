import time
from datetime import datetime, timedelta


def test_evidence_creation_writes_first_version(client):
    case = client.post("/api/cases", json={"title": "TM case"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc A"}).json()

    history = client.get(f"/api/evidence/{ev['id']}/history").json()
    assert len(history) == 1
    assert history[0]["version_number"] == 1
    assert history[0]["snapshot"]["label"] == "Doc A"


def test_approved_review_creates_second_version_and_diff(client):
    case = client.post("/api/cases", json={"title": "TM diff case"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc B"}).json()

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.core.db import SessionLocal
    from app.services.review_service import propose_action, decide

    db = SessionLocal()
    task = propose_action(
        db, case["id"], action_type="CHANGE_VERIFIED_STATUS", target_type="EVIDENCE",
        target_id=ev["id"], proposed_change={"verification_status": "VERIFIED"},
        proposing_agent="TestAgent",
    )
    decide(db, task.id, approve=True, decided_by_user_id="tester", note="approved for test")
    db.close()

    history = client.get(f"/api/evidence/{ev['id']}/history").json()
    assert len(history) == 2
    assert history[1]["snapshot"]["verification_status"] == "VERIFIED"

    cv = client.get(f"/api/evidence/{ev['id']}/current-vs-previous").json()
    assert cv["current"]["snapshot"]["verification_status"] == "VERIFIED"
    assert cv["diff"]["changed_fields"]["verification_status"]["to"] == "VERIFIED"

    diff = client.get(
        f"/api/evidence/{ev['id']}/diff", params={"from_version": 1, "to_version": 2}
    ).json()
    assert "verification_status" in diff["changed_fields"]


def test_time_machine_reconstructs_case_state_at_past_timestamp(client):
    case = client.post("/api/cases", json={"title": "TM reconstruct case"}).json()
    before = datetime.utcnow().isoformat()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc C"}).json()

    snapshot_now = client.get(
        f"/api/cases/{case['id']}/time-machine", params={"at": datetime.utcnow().isoformat()}
    ).json()
    assert any(s["evidence_id"] == ev["id"] for s in snapshot_now["evidence_states"])

    snapshot_before = client.get(
        f"/api/cases/{case['id']}/time-machine", params={"at": before}
    ).json()
    assert not any(s["evidence_id"] == ev["id"] for s in snapshot_before["evidence_states"])


def test_diff_unknown_version_404s(client):
    case = client.post("/api/cases", json={"title": "TM missing version case"}).json()
    ev = client.post(f"/api/cases/{case['id']}/evidence", json={"label": "Doc D"}).json()
    resp = client.get(f"/api/evidence/{ev['id']}/diff", params={"from_version": 1, "to_version": 99})
    assert resp.status_code == 404


def test_claim_creation_writes_first_version(client):
    case = client.post("/api/cases", json={"title": "Claim TM case"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Notice was served."}).json()

    history = client.get(f"/api/claims/{claim['id']}/history").json()
    assert len(history) == 1
    assert history[0]["version_number"] == 1
    assert history[0]["snapshot"]["text"] == "Notice was served."


def test_claim_approval_creates_second_version_and_diff(client):
    case = client.post("/api/cases", json={"title": "Claim TM diff case"}).json()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Payment was made."}).json()

    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.core.db import SessionLocal
    from app.services.review_service import propose_action, decide

    db = SessionLocal()
    task = propose_action(
        db, case["id"], action_type="CHANGE_VERIFIED_STATUS", target_type="CLAIM",
        target_id=claim["id"], proposed_change={"verification_status": "VERIFIED"},
        proposing_agent="TestAgent",
    )
    decide(db, task.id, approve=True, decided_by_user_id="tester", note="approved for test")
    db.close()

    history = client.get(f"/api/claims/{claim['id']}/history").json()
    assert len(history) == 2
    assert history[1]["snapshot"]["verification_status"] == "VERIFIED"

    cv = client.get(f"/api/claims/{claim['id']}/current-vs-previous").json()
    assert cv["diff"]["changed_fields"]["verification_status"]["to"] == "VERIFIED"

    diff = client.get(f"/api/claims/{claim['id']}/diff", params={"from_version": 1, "to_version": 2}).json()
    assert "verification_status" in diff["changed_fields"]


def test_case_time_machine_includes_claim_states(client):
    case = client.post("/api/cases", json={"title": "Claim reconstruct case"}).json()
    before = datetime.utcnow().isoformat()
    claim = client.post(f"/api/cases/{case['id']}/claims", json={"text": "Deadline was met."}).json()

    snapshot_now = client.get(
        f"/api/cases/{case['id']}/time-machine", params={"at": datetime.utcnow().isoformat()}
    ).json()
    assert any(s["claim_id"] == claim["id"] for s in snapshot_now["claim_states"])

    snapshot_before = client.get(f"/api/cases/{case['id']}/time-machine", params={"at": before}).json()
    assert not any(s["claim_id"] == claim["id"] for s in snapshot_before["claim_states"])


def test_demo_seeded_evidence_and_claims_have_time_machine_history(client):
    """Demo-seeded rows must be first-class citizens of the Time Machine too,
    not just API-created ones -- regression guard for the demo seed path."""
    case = client.post("/api/cases/demo/seed/A", json={}).json()

    ev = client.get(f"/api/cases/{case['id']}/evidence").json()[0]
    ev_history = client.get(f"/api/evidence/{ev['id']}/history").json()
    assert len(ev_history) == 1
    assert ev_history[0]["reason"] == "DEMO_SEEDED"

    claim = client.get(f"/api/cases/{case['id']}/claims").json()[0]
    claim_history = client.get(f"/api/claims/{claim['id']}/history").json()
    assert len(claim_history) == 1
    assert claim_history[0]["reason"] == "DEMO_SEEDED"
