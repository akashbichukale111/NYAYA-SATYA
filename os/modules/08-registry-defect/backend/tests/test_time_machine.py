from app.services import time_machine, seed_demo
from app import models
from app.core.ids import new_id, utcnow


def _setup(db_session):
    user = seed_demo._ensure_demo_user(db_session)
    case = models.Case(id=new_id("case"), title="T", owner_user_id=user.id, status="ACTIVE",
                        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(case)
    db_session.commit()
    pkg = models.FilingPackage(id=new_id("pkg"), case_id=case.id, name="P", lifecycle_state="DRAFT",
                                created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(pkg)
    db_session.commit()
    return user, case, pkg


def test_document_history_tracks_versions_without_deleting(db_session):
    user, case, pkg = _setup(db_session)
    doc, v1 = seed_demo._make_text_document(
        db_session, case_id=case.id, package_id=pkg.id, display_name="Doc",
        document_kind="form", text="version one content", user_id=user.id,
    )
    history = time_machine.get_document_history(db_session, filing_package_id=pkg.id)
    assert len(history) == 1
    assert history[0]["document_id"] == doc.id
    assert len(history[0]["versions"]) == 1
    assert history[0]["versions"][0]["is_current"] is True


def test_defect_history_reconstructed_from_audit_log(db_session):
    from app.core.audit import record as audit_record
    user, case, pkg = _setup(db_session)
    fake_defect_id = new_id("dft")
    audit_record(
        db_session, case_id=case.id, actor_user_id=user.id, actor_role="ADVOCATE",
        action="REVIEW_APPROVED", entity_type="Defect", entity_id=fake_defect_id,
        before_state={"decision": "PENDING"}, after_state={"decision": "APPROVED"},
        reason="test", provenance="HUMAN_DECISION",
    )
    db_session.add(models.Defect(
        id=fake_defect_id, case_id=case.id, filing_package_id=pkg.id, defect_type="MISSING_DOCUMENT",
        category="COMPLETENESS", severity="ATTENTION", status="CONFIRMED", description="x",
    ))
    db_session.commit()

    history = time_machine.get_defect_history(db_session, case_id=case.id, filing_package_id=pkg.id)
    entry = next(h for h in history if h["defect_id"] == fake_defect_id)
    assert len(entry["history"]) == 1
    assert entry["history"][0]["action"] == "REVIEW_APPROVED"


def test_requirement_source_history_never_fabricates_recorded_at(db_session):
    from app.services import requirement_engine
    user, case, pkg = _setup(db_session)
    req = requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="X required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist item",
    )
    history = time_machine.get_requirement_source_history(db_session, filing_package_id=pkg.id)
    entry = next(h for h in history if h["requirement_id"] == req.id)
    assert entry["recorded_at"] is not None  # a real ProvenanceRecord exists
    assert entry["source"] == "USER_PROVIDED_CHECKLIST"


def test_submission_snapshot_none_when_never_submitted(db_session):
    user, case, pkg = _setup(db_session)
    snapshot = time_machine.get_submission_snapshot(db_session, filing_package_id=pkg.id)
    assert snapshot is None


def test_build_time_machine_view_returns_all_sections(db_session):
    user, case, pkg = _setup(db_session)
    view = time_machine.build_time_machine_view(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert set(view.keys()) == {
        "filing_package_id", "document_history", "defect_history",
        "objection_history", "requirement_source_history", "last_submission_snapshot",
    }
