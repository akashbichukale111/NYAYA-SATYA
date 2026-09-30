from app.services import metadata_engine
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


def _make_doc_with_metadata(db_session, case, pkg, field_name, value):
    doc = models.Document(id=new_id("doc"), case_id=case.id, filing_package_id=pkg.id,
                           display_name="Doc", status="ACTIVE",
                           created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(doc)
    db_session.commit()
    version = models.DocumentVersion(id=new_id("docv"), document_id=doc.id, case_id=case.id,
                                      version_number=1, original_filename="doc.txt", stored_path="x",
                                      extraction_status="OK", uploaded_at=utcnow().isoformat())
    db_session.add(version)
    db_session.commit()
    db_session.add(models.DocumentMetadata(id=new_id("meta"), document_version_id=version.id,
                                            case_id=case.id, field_name=field_name, field_value=value))
    db_session.commit()
    return doc, version


def test_no_conflict_when_values_match(db_session):
    case, pkg = _setup(db_session)
    _make_doc_with_metadata(db_session, case, pkg, "case_number", "ABC-1")
    _make_doc_with_metadata(db_session, case, pkg, "case_number", "ABC-1")
    conflicts = metadata_engine.detect_metadata_conflicts(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert conflicts == []


def test_conflict_detected_on_mismatched_case_number(db_session):
    case, pkg = _setup(db_session)
    _make_doc_with_metadata(db_session, case, pkg, "case_number", "ABC-1")
    _make_doc_with_metadata(db_session, case, pkg, "case_number", "ABC-2")
    conflicts = metadata_engine.detect_metadata_conflicts(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.status == "UNRESOLVED"
    assert {c.left_value, c.right_value} == {"ABC-1", "ABC-2"}


def test_engine_does_not_decide_which_value_is_correct(db_session):
    case, pkg = _setup(db_session)
    _make_doc_with_metadata(db_session, case, pkg, "party_name", "A. Kumar")
    _make_doc_with_metadata(db_session, case, pkg, "party_name", "A Kumar Singh")
    conflicts = metadata_engine.detect_metadata_conflicts(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert len(conflicts) == 1
    # No "correct_value" or similar field exists on the model at all —
    # the engine has no mechanism to assert correctness.
    assert not hasattr(conflicts[0], "correct_value")
