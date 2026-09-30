from app.services import case_twin, readiness_engine, blocker_engine, causal_graph


def _seed_case_with_one_blocker(db):
    case = case_twin.create_case(db, "Test Case", "civil", [{"name": "A", "role": "plaintiff"}])
    from app.models.hearing import Hearing
    from app.models.evidence import Evidence
    from app.models.requirement import Requirement

    hearing = Hearing(case_id=case.id, is_next="true", purpose="ARGUMENTS", purpose_status="DETERMINED")
    db.add(hearing)
    db.flush()

    ev_missing = Evidence(case_id=case.id, label="Missing Doc", evidence_type="document",
                           availability="MISSING", verification_state="UNVERIFIED", confidence="HIGH")
    ev_ok = Evidence(case_id=case.id, label="Good Doc", evidence_type="document",
                      availability="AVAILABLE", verification_state="VERIFIED", confidence="HIGH")
    db.add_all([ev_missing, ev_ok])
    db.flush()

    req_blocked = Requirement(case_id=case.id, hearing_id=hearing.id, category="DOCUMENTS",
                               description="Missing doc filed", status="UNKNOWN", reason="",
                               evidence_refs=[ev_missing.id], confidence="UNKNOWN")
    req_ok = Requirement(case_id=case.id, hearing_id=hearing.id, category="EVIDENCE",
                          description="Good doc filed", status="UNKNOWN", reason="",
                          evidence_refs=[ev_ok.id], confidence="UNKNOWN")
    db.add_all([req_blocked, req_ok])
    db.flush()
    return case, hearing, req_blocked, req_ok, ev_missing, ev_ok


def test_run_readiness_audit_creates_one_open_blocker(db_session):
    case, hearing, req_blocked, req_ok, ev_missing, ev_ok = _seed_case_with_one_blocker(db_session)

    snapshot = readiness_engine.run_readiness_audit(db_session, case.id)

    from app.models.blocker import Blocker
    blockers = db_session.query(Blocker).filter(Blocker.case_id == case.id).all()
    assert len(blockers) == 1
    assert blockers[0].status == "OPEN"
    assert blockers[0].requirement_id == req_blocked.id
    assert snapshot["overall"] in ("BLOCKED", "CONDITIONAL")
    assert snapshot["unresolved_count"] == 1
    assert snapshot["satisfied_count"] == 1


def test_blocker_resolves_when_evidence_becomes_available(db_session):
    case, hearing, req_blocked, req_ok, ev_missing, ev_ok = _seed_case_with_one_blocker(db_session)
    readiness_engine.run_readiness_audit(db_session, case.id)

    from app.models.blocker import Blocker
    from app.models.evidence import Evidence

    # Fix the underlying evidence, exactly like a human uploading the doc.
    ev = db_session.query(Evidence).filter(Evidence.id == ev_missing.id).first()
    ev.availability = "AVAILABLE"
    ev.verification_state = "VERIFIED"
    db_session.flush()

    snapshot = readiness_engine.run_readiness_audit(db_session, case.id)
    blockers = db_session.query(Blocker).filter(Blocker.case_id == case.id).all()
    assert len(blockers) == 1
    assert blockers[0].status == "RESOLVED"
    assert snapshot["overall"] == "READY"


def test_causal_graph_has_edges_for_open_blocker(db_session):
    case, *_ = _seed_case_with_one_blocker(db_session)
    readiness_engine.run_readiness_audit(db_session, case.id)

    graph = causal_graph.get_graph(db_session, case.id)
    assert len(graph["edges"]) > 0
    edge_types = {(e["from"]["type"], e["to"]["type"]) for e in graph["edges"]}
    assert ("HEARING", "REQUIREMENT") in edge_types
    assert ("REQUIREMENT", "BLOCKER") in edge_types
