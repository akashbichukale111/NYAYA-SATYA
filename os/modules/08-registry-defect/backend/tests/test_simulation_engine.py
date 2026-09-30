from app.services import simulation_engine
from app import models
from app.core.ids import new_id, utcnow


def _setup(db_session):
    case = models.Case(id=new_id("case"), title="T", status="ACTIVE",
                        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(case)
    db_session.commit()
    pkg = models.FilingPackage(id=new_id("pkg"), case_id=case.id, name="P", lifecycle_state="DRAFT",
                                created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(pkg)
    db_session.commit()
    return case, pkg


def test_counterfactual_simulation_is_non_destructive(db_session):
    case, pkg = _setup(db_session)
    doc = models.Document(id=new_id("doc"), case_id=case.id, filing_package_id=pkg.id,
                           display_name="Petition", status="ACTIVE",
                           created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(doc)
    db_session.commit()

    result = simulation_engine.run_counterfactual(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        scenario="REMOVE_REQUIRED_DOCUMENT", params={"document_id": doc.id}, user_id=None,
    )
    assert result["recognized"] is True
    assert len(result["new_defects"]) == 1

    # The real Document row must be untouched.
    still_there = db_session.query(models.Document).filter(models.Document.id == doc.id).first()
    assert still_there is not None
    assert still_there.status == "ACTIVE"


def test_counterfactual_unrecognized_scenario_runs_nothing(db_session):
    case, pkg = _setup(db_session)
    result = simulation_engine.run_counterfactual(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        scenario="NOT_A_REAL_SCENARIO", params={}, user_id=None,
    )
    assert result["recognized"] is False
    assert result["new_defects"] == []


def test_crash_test_runs_all_twelve_scenarios(db_session):
    case, pkg = _setup(db_session)
    result = simulation_engine.run_crash_test_suite(db_session, case_id=case.id, filing_package_id=pkg.id, user_id=None)
    assert len(result["scenarios"]) == 12
    assert len(result["scenarios"]) == len(simulation_engine.CRASH_TEST_SCENARIOS)
    assert result["non_destructive"] is True


def test_crash_test_creates_no_real_defects_or_documents(db_session):
    case, pkg = _setup(db_session)
    simulation_engine.run_crash_test_suite(db_session, case_id=case.id, filing_package_id=pkg.id, user_id=None)
    real_defects = db_session.query(models.Defect).filter(models.Defect.filing_package_id == pkg.id).count()
    real_docs = db_session.query(models.Document).filter(models.Document.filing_package_id == pkg.id).count()
    assert real_defects == 0
    assert real_docs == 0


def test_crash_test_persists_one_simulation_record(db_session):
    case, pkg = _setup(db_session)
    simulation_engine.run_crash_test_suite(db_session, case_id=case.id, filing_package_id=pkg.id, user_id=None)
    sims = db_session.query(models.Simulation).filter(
        models.Simulation.filing_package_id == pkg.id, models.Simulation.simulation_type == "CRASH_TEST"
    ).all()
    assert len(sims) == 1
    assert sims[0].is_destructive is False


def test_all_crash_test_scenarios_from_spec_are_present():
    expected = {
        "REMOVE_REQUIRED_DOCUMENT", "REMOVE_REFERENCED_ANNEXURE", "INTRODUCE_METADATA_CONFLICT",
        "SUBMIT_DUPLICATE_VERSION", "SUPERSEDE_CURRENT_DOCUMENT", "INVALIDATE_SOURCE",
        "CREATE_UNRESOLVED_OBJECTION", "REMOVE_CORRECTION_EVIDENCE",
        "CHANGE_REQUIREMENT_STATUS_TO_UNKNOWN", "BREAK_DOCUMENT_REFERENCE", "CORRUPT_DOCUMENT",
        "INTRODUCE_PROMPT_INJECTION",
    }
    assert set(simulation_engine.CRASH_TEST_SCENARIOS) == expected
