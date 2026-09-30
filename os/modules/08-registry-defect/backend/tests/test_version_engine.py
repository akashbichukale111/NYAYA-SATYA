from app.services import version_engine
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


def _make_doc_version(db_session, case, pkg, filename):
    doc = models.Document(id=new_id("doc"), case_id=case.id, filing_package_id=pkg.id,
                           display_name=filename, status="ACTIVE",
                           created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(doc)
    db_session.commit()
    version = models.DocumentVersion(id=new_id("docv"), document_id=doc.id, case_id=case.id,
                                      version_number=1, original_filename=filename, stored_path="x",
                                      extraction_status="OK", uploaded_at=utcnow().isoformat())
    db_session.add(version)
    doc.current_version_id = version.id
    db_session.commit()
    return doc, version


def test_propose_supersession_does_not_change_current_version(db_session):
    case, pkg = _setup(db_session)
    doc_a, v_a = _make_doc_version(db_session, case, pkg, "a.txt")
    doc_b, v_b = _make_doc_version(db_session, case, pkg, "b.txt")

    version_engine.propose_supersession(db_session, case_id=case.id, predecessor_version_id=v_a.id, successor_version_id=v_b.id)

    db_session.refresh(doc_a)
    assert doc_a.current_version_id == v_a.id  # unchanged until confirmed
    assert doc_a.status == "ACTIVE"


def test_confirm_supersession_marks_predecessor_document_superseded(db_session):
    case, pkg = _setup(db_session)
    doc_a, v_a = _make_doc_version(db_session, case, pkg, "a.txt")
    doc_b, v_b = _make_doc_version(db_session, case, pkg, "b.txt")

    sup = version_engine.propose_supersession(db_session, case_id=case.id, predecessor_version_id=v_a.id, successor_version_id=v_b.id)
    version_engine.confirm_supersession(db_session, supersession_id=sup.id)

    db_session.refresh(doc_a)
    db_session.refresh(doc_b)
    assert doc_a.status == "SUPERSEDED"
    assert doc_b.current_version_id == v_b.id


def test_historical_versions_never_deleted(db_session):
    case, pkg = _setup(db_session)
    doc_a, v_a = _make_doc_version(db_session, case, pkg, "a.txt")
    doc_b, v_b = _make_doc_version(db_session, case, pkg, "b.txt")
    sup = version_engine.propose_supersession(db_session, case_id=case.id, predecessor_version_id=v_a.id, successor_version_id=v_b.id)
    version_engine.confirm_supersession(db_session, supersession_id=sup.id)

    # v_a still exists in the database, unmodified in identity, just no
    # longer "current" on its (now-superseded) document.
    still_there = db_session.query(models.DocumentVersion).filter(models.DocumentVersion.id == v_a.id).first()
    assert still_there is not None


def test_get_version_history_orders_oldest_to_newest(db_session):
    case, pkg = _setup(db_session)
    doc = models.Document(id=new_id("doc"), case_id=case.id, filing_package_id=pkg.id,
                           display_name="Doc", status="ACTIVE",
                           created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(doc)
    db_session.commit()
    v1 = models.DocumentVersion(id=new_id("docv"), document_id=doc.id, case_id=case.id, version_number=1,
                                 original_filename="v1.txt", stored_path="x", extraction_status="OK",
                                 uploaded_at=utcnow().isoformat())
    v2 = models.DocumentVersion(id=new_id("docv"), document_id=doc.id, case_id=case.id, version_number=2,
                                 original_filename="v2.txt", stored_path="x", extraction_status="OK",
                                 uploaded_at=utcnow().isoformat())
    db_session.add_all([v1, v2])
    doc.current_version_id = v2.id
    db_session.commit()

    history = version_engine.get_version_history(db_session, document_id=doc.id)
    assert [h["version_number"] for h in history] == [1, 2]
    assert history[1]["is_current"] is True
    assert history[0]["is_current"] is False
