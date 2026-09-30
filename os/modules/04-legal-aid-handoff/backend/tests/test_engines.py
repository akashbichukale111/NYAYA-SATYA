from database import SessionLocal
from models import Case, Fact, TimelineEvent, FactStatus, Sensitivity, Role
from facts.engines import recompute_conflicts, missing_information_report
from handoff.generator import generate_packet
from privacy.engine import is_allowed
from handoff.crash_test import run_crash_tests


def make_db():
    return SessionLocal()


def test_conflict_detection_finds_date_conflict():
    db = make_db()
    case = Case(title="t")
    db.add(case)
    db.commit()
    db.refresh(case)

    db.add_all([
        TimelineEvent(case_id=case.id, event_date="2026-03-12", description="notice: citizen says 12 March"),
        TimelineEvent(case_id=case.id, event_date="2026-03-15", description="notice: document says 15 March"),
    ])
    db.commit()

    conflicts = recompute_conflicts(db, case.id)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type.value == "DATE_CONFLICT"
    db.close()


def test_no_conflict_when_dates_agree():
    db = make_db()
    case = Case(title="t2")
    db.add(case)
    db.commit()
    db.refresh(case)

    db.add_all([
        TimelineEvent(case_id=case.id, event_date="2026-03-12", description="notice: citizen says 12 March"),
        TimelineEvent(case_id=case.id, event_date="2026-03-12", description="notice: document says 12 March"),
    ])
    db.commit()
    conflicts = recompute_conflicts(db, case.id)
    assert len(conflicts) == 0
    db.close()


def test_missing_information_flags_no_deadline_and_no_documents():
    db = make_db()
    case = Case(title="t3")
    db.add(case)
    db.commit()
    db.refresh(case)

    report = missing_information_report(db, case.id)
    items = [r["item"] for r in report]
    assert any("deadline" in i.lower() for i in items)
    assert any("document" in i.lower() for i in items)
    db.close()


def test_privacy_engine_blocks_over_ceiling_field():
    assert is_allowed(Sensitivity.HIGHLY_SENSITIVE, Role.CITIZEN) is False
    assert is_allowed(Sensitivity.PUBLIC, Role.CITIZEN) is True
    assert is_allowed(Sensitivity.HIGHLY_SENSITIVE, Role.ADVOCATE) is True


def test_handoff_packet_excludes_highly_sensitive_fact_for_paralegal():
    db = make_db()
    case = Case(title="t4")
    db.add(case)
    db.commit()
    db.refresh(case)

    db.add_all([
        Fact(case_id=case.id, label="secret", statement="sensitive", status=FactStatus.USER_REPORTED,
             sensitivity=Sensitivity.HIGHLY_SENSITIVE),
        Fact(case_id=case.id, label="public_fact", statement="not sensitive", status=FactStatus.USER_REPORTED,
             sensitivity=Sensitivity.PUBLIC),
    ])
    db.commit()

    version = generate_packet(db, case, "Initial Legal-Aid Review", Role.PARALEGAL, Role.LEGAL_AID_WORKER)
    included_labels = [f.label for f in db.query(Fact).filter(Fact.id.in_(version.included_fact_ids)).all()]
    assert "public_fact" in included_labels
    assert "secret" not in included_labels
    assert any(n["field"] == "secret" for n in version.excluded_field_notes)
    db.close()


def test_handoff_blocked_when_critical_fact_unsupported():
    db = make_db()
    case = Case(title="t5")
    db.add(case)
    db.commit()
    db.refresh(case)
    db.add(Fact(case_id=case.id, label="unknown_fact", statement="?", status=FactStatus.NOT_PROVIDED))
    db.commit()

    version = generate_packet(db, case, "Initial Legal-Aid Review", Role.PARALEGAL, Role.LEGAL_AID_WORKER)
    assert version.quality_checks["overall"] == "BLOCKED"
    db.close()


def test_crash_test_battery_all_pass():
    results = run_crash_tests()
    assert all(r["result"] == "PASS" for r in results)
    assert len(results) == 5
