from app.services import readiness_engine, crash_test_engine
from app.models.evidence import Evidence
from app.models.requirement import Requirement


def _seed_ready_case(db):
    from app.services import case_twin
    from app.models.hearing import Hearing

    case = case_twin.create_case(db, "Crash Test Case", "civil", [])
    hearing = Hearing(case_id=case.id, is_next="true", purpose="ARGUMENTS", purpose_status="DETERMINED")
    db.add(hearing)
    db.flush()

    ev = Evidence(case_id=case.id, label="Service Affidavit", evidence_type="affidavit",
                  availability="AVAILABLE", verification_state="VERIFIED", confidence="HIGH")
    db.add(ev)
    db.flush()

    req = Requirement(case_id=case.id, hearing_id=hearing.id, category="SERVICE",
                       description="Service affidavit filed", status="UNKNOWN", reason="",
                       evidence_refs=[ev.id], confidence="UNKNOWN")
    db.add(req)
    db.flush()
    readiness_engine.run_readiness_audit(db, case.id)
    return case, req, ev


def test_crash_test_never_mutates_live_evidence(db_session):
    case, req, ev = _seed_ready_case(db_session)
    crash_test_engine.run_crash_test(db_session, case.id, "remove_evidence")

    fresh = db_session.query(Evidence).filter(Evidence.id == ev.id).first()
    assert fresh is not None  # still exists in the live table


def test_crash_test_remove_evidence_changes_readiness(db_session):
    case, req, ev = _seed_ready_case(db_session)
    result = crash_test_engine.run_crash_test(db_session, case.id, "remove_evidence")
    assert result.passed == "true"
    assert result.mutation == "remove_evidence"


def test_crash_test_add_irrelevant_document_does_not_change_readiness(db_session):
    case, req, ev = _seed_ready_case(db_session)
    result = crash_test_engine.run_crash_test(db_session, case.id, "add_irrelevant_document")
    assert result.passed == "true"
    assert result.observed_effect == "no_change"


def test_crash_test_rejects_unknown_mutation(db_session):
    case, req, ev = _seed_ready_case(db_session)
    try:
        crash_test_engine.run_crash_test(db_session, case.id, "not_a_real_mutation")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_run_all_crash_tests_returns_one_per_mutation(db_session):
    case, req, ev = _seed_ready_case(db_session)
    results = crash_test_engine.run_all_crash_tests(db_session, case.id)
    assert len(results) == len(crash_test_engine.MUTATIONS)
