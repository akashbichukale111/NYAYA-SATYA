from app.services import requirement_engine, precheck, verification_engine
from app.services.parsing import parse_file
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


def _upload_text_doc(db_session, case, pkg, display_name, text):
    parsed = parse_file(f"{display_name}.txt", text.encode())
    doc = models.Document(id=new_id("doc"), case_id=case.id, filing_package_id=pkg.id,
                           display_name=display_name, status="ACTIVE",
                           created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(doc)
    db_session.commit()
    version = models.DocumentVersion(id=new_id("docv"), document_id=doc.id, case_id=case.id, version_number=1,
                                      original_filename=f"{display_name}.txt", stored_path="x",
                                      extraction_status=parsed.extraction_status, extracted_text=parsed.extracted_text,
                                      sha256=parsed.sha256, uploaded_at=utcnow().isoformat())
    db_session.add(version)
    doc.current_version_id = version.id
    db_session.commit()
    return doc, version


def test_verify_defect_reports_still_failing_when_condition_persists(db_session):
    case, pkg = _setup(db_session)
    requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Affidavit required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist",
        target_reference_label="Affidavit",
    )
    precheck.run_precheck(db_session, case_id=case.id, filing_package_id=pkg.id)
    defect = db_session.query(models.Defect).filter(models.Defect.filing_package_id == pkg.id).first()

    verification = verification_engine.verify_defect(db_session, defect_id=defect.id)
    assert verification.result == "STILL_FAILING"

    db_session.refresh(defect)
    # Crucially: a failed re-check does NOT mark the defect resolved.
    assert defect.status != "RESOLVED"


def test_verify_defect_reports_verified_after_real_fix(db_session):
    case, pkg = _setup(db_session)
    requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Affidavit required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist",
        target_reference_label="Affidavit",
    )
    precheck.run_precheck(db_session, case_id=case.id, filing_package_id=pkg.id)
    defect = db_session.query(models.Defect).filter(models.Defect.filing_package_id == pkg.id).first()

    # Actually fix it: upload the affidavit and rebuild the checklist.
    _upload_text_doc(db_session, case, pkg, "Affidavit", "This is the affidavit content.")
    from app.services import checklist_engine
    checklist_engine.build_checklist(db_session, case_id=case.id, filing_package_id=pkg.id)

    verification = verification_engine.verify_defect(db_session, defect_id=defect.id)
    assert verification.result == "VERIFIED"

    db_session.refresh(defect)
    # VERIFIED, not yet RESOLVED — a human must still confirm (see review gate).
    assert defect.status == "VERIFIED"
    assert defect.status != "RESOLVED"


def test_verify_defect_never_auto_resolves_merely_because_a_file_changed(db_session):
    """The spec's exact wording: uploading an unrelated file must not
    flip a defect to resolved."""
    case, pkg = _setup(db_session)
    requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Affidavit required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist",
        target_reference_label="Affidavit",
    )
    precheck.run_precheck(db_session, case_id=case.id, filing_package_id=pkg.id)
    defect = db_session.query(models.Defect).filter(models.Defect.filing_package_id == pkg.id).first()

    # Upload something totally unrelated.
    _upload_text_doc(db_session, case, pkg, "Unrelated Note", "This has nothing to do with the affidavit.")

    verification = verification_engine.verify_defect(db_session, defect_id=defect.id)
    assert verification.result == "STILL_FAILING"
    db_session.refresh(defect)
    assert defect.status != "RESOLVED"


def test_verify_defect_creates_review_task_on_verified(db_session):
    case, pkg = _setup(db_session)
    requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Proof required",
        source="USER_PROVIDED_CHECKLIST", source_reference="checklist",
        target_reference_label="Proof",
    )
    precheck.run_precheck(db_session, case_id=case.id, filing_package_id=pkg.id)
    defect = db_session.query(models.Defect).filter(models.Defect.filing_package_id == pkg.id).first()
    _upload_text_doc(db_session, case, pkg, "Proof", "Proof content.")
    from app.services import checklist_engine
    checklist_engine.build_checklist(db_session, case_id=case.id, filing_package_id=pkg.id)

    verification_engine.verify_defect(db_session, defect_id=defect.id)

    task = db_session.query(models.ReviewTask).filter(
        models.ReviewTask.target_id == defect.id,
        models.ReviewTask.action_requested == "CONFIRM_RESOLUTION_AFTER_VERIFICATION",
    ).first()
    assert task is not None
    assert task.decision == "PENDING"
