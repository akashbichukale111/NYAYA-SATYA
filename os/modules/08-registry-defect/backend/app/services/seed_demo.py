"""
Deterministic demo data seeding.

Creates exactly 3 synthetic cases (Demo A/B/C from the spec), each
clearly marked is_demo=True. Every screen showing demo data must check
this flag and render the "DEMONSTRATION DATA — NOT A REAL CASE" banner
(enforced in the frontend by reading Case.is_demo).

All demo requirements are created with source=USER_PROVIDED_CHECKLIST
and an explicit source_reference describing the synthetic checklist —
never CONFIGURED_REGISTRY_RULE, since no real registry rule exists here.
"""
import bcrypt
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow
from app.services import requirement_engine, precheck as precheck_service
from app.services.parsing import sha256_bytes

DEMO_MARKER = "DEMONSTRATION DATA — NOT A REAL CASE"


def _ensure_demo_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == "demo.advocate@example.invalid").first()
    if user:
        return user
    user = models.User(
        id=new_id("user"), name="Demo Advocate", email="demo.advocate@example.invalid",
        role="ADVOCATE",
        hashed_password=bcrypt.hashpw(b"demo-not-a-real-password", bcrypt.gensalt()).decode("utf-8"),
        created_at=utcnow().isoformat(), is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_text_document(db: Session, *, case_id, package_id, display_name, document_kind, text, user_id):
    from app.services import parsing, attachment_engine
    content = text.encode("utf-8")
    parsed = parsing.parse_file(f"{display_name}.txt", content)

    document = models.Document(
        id=new_id("doc"), case_id=case_id, filing_package_id=package_id,
        display_name=display_name, document_kind=document_kind, status="ACTIVE",
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    version = models.DocumentVersion(
        id=new_id("docv"), document_id=document.id, case_id=case_id, version_number=1,
        original_filename=f"{display_name}.txt", stored_path=f"demo://{document.id}",
        mime_type="text/plain", detected_format="TXT", size_bytes=len(content),
        sha256=parsed.sha256, extracted_text=parsed.extracted_text,
        extraction_status=parsed.extraction_status, extraction_error=parsed.extraction_error,
        page_count=None, uploaded_at=utcnow().isoformat(), uploaded_by_user_id=user_id,
        source_location_known=True,
    )
    db.add(version)
    document.current_version_id = version.id
    db.commit()
    db.refresh(version)

    for section in parsed.sections:
        db.add(models.DocumentSection(
            id=new_id("sec"), document_version_id=version.id, case_id=case_id,
            section_type=section.section_type, section_index=section.section_index,
            text_excerpt=section.text_excerpt, location_known=section.location_known,
        ))
    db.commit()

    if parsed.extraction_status == "OK":
        attachment_engine.detect_and_store_references(
            db, case_id=case_id, filing_package_id=package_id, document_version=version,
        )
    return document, version


def _add_metadata(db, version_id, case_id, field_name, value, source="EXTRACTED"):
    db.add(models.DocumentMetadata(
        id=new_id("meta"), document_version_id=version_id, case_id=case_id,
        field_name=field_name, field_value=value, source=source, confidence="USER_REPORTED",
    ))
    db.commit()


def seed_demo_a(db: Session, user: models.User) -> models.Case:
    """Demo A — Missing Attachment: a filing references Annexure B but the
    package lacks it."""
    case = models.Case(
        id=new_id("case"), title="Demo A — Missing Attachment Reference",
        case_reference="DEMO-A-001", owner_user_id=user.id, status="ACTIVE", is_demo=True,
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    package = models.FilingPackage(
        id=new_id("pkg"), case_id=case.id, name="Initial Petition Package",
        lifecycle_state="DRAFT", created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(package)
    db.commit()
    db.refresh(package)

    petition_text = (
        "PETITION\n\nCase Number: DEMO-A-001\n\n"
        "The petitioner respectfully submits this petition along with supporting materials. "
        "A copy of the identity document is attached as Annexure A. "
        "A copy of the prior order is attached as Annexure B. "
        "The petitioner requests the registry to accept this filing for processing."
    )
    _make_text_document(db, case_id=case.id, package_id=package.id, display_name="Petition",
                         document_kind="petition", text=petition_text, user_id=user.id)

    annexure_a_text = "ANNEXURE A\n\nIdentity Document Copy\nCase Number: DEMO-A-001"
    _make_text_document(db, case_id=case.id, package_id=package.id, display_name="Annexure A",
                         document_kind="annexure", text=annexure_a_text, user_id=user.id)

    # Annexure B is deliberately NOT uploaded — this is the defect.

    requirement_engine.create_requirement(
        db, case_id=case.id, filing_package_id=package.id,
        requirement_type="REFERENCE_REQUIRED",
        description="Any annexure referenced in the petition text must be present in the filing package.",
        source="USER_PROVIDED_CHECKLIST",
        source_reference="Demo checklist item: 'All referenced annexures must be attached'",
        target_reference_label="Annexure B",
    )

    precheck_service.run_precheck(db, case_id=case.id, filing_package_id=package.id)
    return case


def seed_demo_b(db: Session, user: models.User) -> models.Case:
    """Demo B — Metadata Conflict: two documents contain inconsistent case
    metadata."""
    case = models.Case(
        id=new_id("case"), title="Demo B — Metadata Conflict",
        case_reference="DEMO-B-001", owner_user_id=user.id, status="ACTIVE", is_demo=True,
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    package = models.FilingPackage(
        id=new_id("pkg"), case_id=case.id, name="Affidavit Package",
        lifecycle_state="DRAFT", created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(package)
    db.commit()
    db.refresh(package)

    aff_text = "AFFIDAVIT\n\nCase Number: DEMO-B-001\nParty Name: A. Kumar\n\nI affirm the contents of this filing are true."
    _, aff_version = _make_text_document(db, case_id=case.id, package_id=package.id, display_name="Affidavit",
                                          document_kind="affidavit", text=aff_text, user_id=user.id)
    _add_metadata(db, aff_version.id, case.id, "case_number", "DEMO-B-001")
    _add_metadata(db, aff_version.id, case.id, "party_name", "A. Kumar")

    form_text = "APPLICATION FORM\n\nCase Number: DEMO-B-002\nParty Name: A. Kumar\n\nApplication for registration."
    _, form_version = _make_text_document(db, case_id=case.id, package_id=package.id, display_name="Application Form",
                                           document_kind="application", text=form_text, user_id=user.id)
    _add_metadata(db, form_version.id, case.id, "case_number", "DEMO-B-002")  # deliberate conflict
    _add_metadata(db, form_version.id, case.id, "party_name", "A. Kumar")

    requirement_engine.create_requirement(
        db, case_id=case.id, filing_package_id=package.id,
        requirement_type="DOCUMENT_REQUIRED",
        description="An affidavit must be included in the package.",
        source="USER_PROVIDED_CHECKLIST",
        source_reference="Demo checklist item: 'Affidavit required'",
        target_reference_label="Affidavit",
    )

    precheck_service.run_precheck(db, case_id=case.id, filing_package_id=package.id)
    return case


def seed_demo_c(db: Session, user: models.User) -> models.Case:
    """Demo C — Objection + Correction: registry objection exists, a
    correction document is submitted, verification is pending."""
    case = models.Case(
        id=new_id("case"), title="Demo C — Objection and Correction Lifecycle",
        case_reference="DEMO-C-001", owner_user_id=user.id, status="ACTIVE", is_demo=True,
        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    package = models.FilingPackage(
        id=new_id("pkg"), case_id=case.id, name="Resubmission Package",
        lifecycle_state="DRAFT", created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(package)
    db.commit()
    db.refresh(package)

    petition_text = "PETITION\n\nCase Number: DEMO-C-001\n\nThe petitioner submits this filing for registry review."
    _make_text_document(db, case_id=case.id, package_id=package.id, display_name="Petition",
                         document_kind="petition", text=petition_text, user_id=user.id)

    objection = models.RegistryObjection(
        id=new_id("obj"), case_id=case.id, filing_package_id=package.id,
        original_text="Annexure missing: proof of authorization was not found in the submitted package.",
        source_reference="Demo registry communication, entered manually",
        status="OPEN", created_at=utcnow().isoformat(), updated_at=utcnow().isoformat(),
    )
    db.add(objection)
    db.commit()
    db.refresh(objection)

    precheck_service.run_precheck(db, case_id=case.id, filing_package_id=package.id)

    # Correction planned and simulated-submitted against the objection's
    # linked defect.
    linked_defect = db.query(models.Defect).filter(models.Defect.id == objection.linked_defect_id).first()
    correction = models.CorrectionRequest(
        id=new_id("creq"), case_id=case.id, filing_package_id=package.id,
        defect_id=linked_defect.id if linked_defect else None, objection_id=objection.id,
        description="Attach proof of authorization document to resolve the registry objection.",
        suggested_action="ATTACH_MISSING_REFERENCE", status="SUBMITTED",
        created_at=utcnow().isoformat(),
    )
    db.add(correction)
    objection.status = "CORRECTION_SUBMITTED"
    db.commit()
    db.refresh(correction)

    authorization_text = "AUTHORIZATION\n\nCase Number: DEMO-C-001\nThis document authorizes the filing on behalf of the petitioner."
    _, auth_version = _make_text_document(db, case_id=case.id, package_id=package.id, display_name="Proof of Authorization",
                                           document_kind="authorization", text=authorization_text, user_id=user.id)

    submission = models.CorrectionSubmission(
        id=new_id("csub"), case_id=case.id, correction_request_id=correction.id,
        document_version_id=auth_version.id, note="Simulated correction submission for demo purposes.",
        submitted_at=utcnow().isoformat(), submitted_by_user_id=user.id, simulated=True,
    )
    db.add(submission)

    verification = models.Verification(
        id=new_id("ver"), case_id=case.id, target_type="CORRECTION", target_id=correction.id,
        result="PENDING", notes="Verification has not yet been run against the resubmitted package.",
        verified_at=utcnow().isoformat(),
    )
    db.add(verification)
    db.commit()

    return case


def seed_all_demo_cases(db: Session) -> list[str]:
    user = _ensure_demo_user(db)
    existing = db.query(models.Case).filter(models.Case.is_demo == True).count()  # noqa: E712
    if existing > 0:
        return [c.id for c in db.query(models.Case).filter(models.Case.is_demo == True).all()]  # noqa: E712
    case_a = seed_demo_a(db, user)
    case_b = seed_demo_b(db, user)
    case_c = seed_demo_c(db, user)
    return [case_a.id, case_b.id, case_c.id]
