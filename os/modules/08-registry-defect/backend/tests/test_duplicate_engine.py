from app.services import duplicate_engine
from app import models
from app.core.ids import new_id, sha256_text, utcnow


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


def _make_version(db_session, case, pkg, text, sha=None):
    doc = models.Document(id=new_id("doc"), case_id=case.id, filing_package_id=pkg.id,
                           display_name="Doc", status="ACTIVE",
                           created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(doc)
    db_session.commit()
    version = models.DocumentVersion(
        id=new_id("docv"), document_id=doc.id, case_id=case.id, version_number=1,
        original_filename="doc.txt", stored_path="x", extraction_status="OK",
        extracted_text=text, sha256=sha or sha256_text(text), uploaded_at=utcnow().isoformat(),
    )
    db_session.add(version)
    db_session.commit()
    return version


def test_hash_duplicate_detected(db_session):
    case, pkg = _setup(db_session)
    _make_version(db_session, case, pkg, "identical content", sha="samehash123")
    _make_version(db_session, case, pkg, "identical content", sha="samehash123")
    groups = duplicate_engine.detect_duplicates(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert len(groups) == 1
    assert groups[0].duplicate_type == "HASH_DUPLICATE"
    assert len(groups[0].member_document_version_ids) == 2


def test_no_duplicate_for_distinct_documents(db_session):
    case, pkg = _setup(db_session)
    _make_version(db_session, case, pkg, "The petitioner requests relief under section 5.")
    _make_version(db_session, case, pkg, "This is a completely different affidavit about something else.")
    groups = duplicate_engine.detect_duplicates(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert groups == []


def test_possible_content_duplicate_detected_for_near_identical_text(db_session):
    case, pkg = _setup(db_session)
    base_text = "PETITION\n\n" + ("The petitioner respectfully requests the court's attention. " * 20)
    near_identical = base_text + "Filed on Monday."
    _make_version(db_session, case, pkg, base_text, sha="hashA")
    _make_version(db_session, case, pkg, near_identical, sha="hashB")
    groups = duplicate_engine.detect_duplicates(db_session, case_id=case.id, filing_package_id=pkg.id)
    assert len(groups) == 1
    assert groups[0].duplicate_type == "POSSIBLE_CONTENT_DUPLICATE"
    assert "similarity ratio" in groups[0].similarity_evidence.lower()


def test_duplicate_engine_never_deletes_anything(db_session):
    case, pkg = _setup(db_session)
    _make_version(db_session, case, pkg, "same text", sha="dupA")
    _make_version(db_session, case, pkg, "same text", sha="dupA")
    duplicate_engine.detect_duplicates(db_session, case_id=case.id, filing_package_id=pkg.id)
    remaining_versions = db_session.query(models.DocumentVersion).filter(
        models.DocumentVersion.case_id == case.id
    ).count()
    assert remaining_versions == 2  # nothing removed
