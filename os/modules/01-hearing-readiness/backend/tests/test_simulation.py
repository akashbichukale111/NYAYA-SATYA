from app.services import readiness_engine, simulation_engine
from app.models.evidence import Evidence
from app.models.requirement import Requirement


def _seed_blocked_case(db):
    from app.services import case_twin
    from app.models.hearing import Hearing

    case = case_twin.create_case(db, "Sim Test Case", "civil", [])
    hearing = Hearing(case_id=case.id, is_next="true", purpose="ARGUMENTS", purpose_status="DETERMINED")
    db.add(hearing)
    db.flush()

    ev = Evidence(case_id=case.id, label="Missing Doc", evidence_type="document",
                  availability="MISSING", verification_state="UNVERIFIED", confidence="HIGH")
    db.add(ev)
    db.flush()

    req = Requirement(case_id=case.id, hearing_id=hearing.id, category="DOCUMENTS",
                       description="Doc filed", status="UNKNOWN", reason="", evidence_refs=[ev.id],
                       confidence="UNKNOWN")
    db.add(req)
    db.flush()
    readiness_engine.run_readiness_audit(db, case.id)
    return case, req, ev


def test_simulation_does_not_mutate_live_evidence(db_session):
    case, req, ev = _seed_blocked_case(db_session)

    simulation_engine.simulate(db_session, case.id, [{"type": "resolve_evidence", "evidence_id": ev.id}])

    # Re-fetch fresh from DB: live row must be untouched.
    fresh = db_session.query(Evidence).filter(Evidence.id == ev.id).first()
    assert fresh.availability == "MISSING"
    assert fresh.verification_state == "UNVERIFIED"


def test_simulation_shows_blocker_would_resolve(db_session):
    case, req, ev = _seed_blocked_case(db_session)

    record = simulation_engine.simulate(
        db_session, case.id, [{"type": "resolve_evidence", "evidence_id": ev.id}]
    )
    assert record.baseline_readiness["overall"] in ("BLOCKED", "CONDITIONAL")
    assert record.simulated_readiness["overall"] == "READY"
    assert len(record.diff["resolved_blockers"]) == 1


def test_simulation_is_labeled_simulation_only(db_session):
    case, req, ev = _seed_blocked_case(db_session)
    record = simulation_engine.simulate(db_session, case.id, [])
    assert record.to_dict()["label"] == "SIMULATION ONLY"
