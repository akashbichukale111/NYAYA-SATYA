from app.services import requirement_engine
from app.core.enums import RequirementSourceType, RequirementStatus, VerificationStatus
from app import models
from app.core.ids import new_id, utcnow


def _make_case_and_package(db_session):
    case = models.Case(id=new_id("case"), title="T", owner_user_id=None, status="ACTIVE",
                        created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(case)
    db_session.commit()
    pkg = models.FilingPackage(id=new_id("pkg"), case_id=case.id, name="P", lifecycle_state="DRAFT",
                                created_at=utcnow().isoformat(), updated_at=utcnow().isoformat())
    db_session.add(pkg)
    db_session.commit()
    return case, pkg


def test_requirement_with_user_checklist_source_is_active(db_session):
    case, pkg = _make_case_and_package(db_session)
    req = requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Annexure A required",
        source=RequirementSourceType.USER_PROVIDED_CHECKLIST.value,
        source_reference="Uploaded checklist.pdf item 1",
    )
    assert req.status == RequirementStatus.ACTIVE.value
    assert req.verification_status == VerificationStatus.SOURCE_SUPPORTED.value


def test_requirement_with_unknown_source_is_never_active(db_session):
    case, pkg = _make_case_and_package(db_session)
    req = requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="DOCUMENT_REQUIRED", description="Some requirement with no real source",
        source=RequirementSourceType.UNKNOWN.value,
    )
    # Never guesses: unknown source must never be marked ACTIVE/verified.
    assert req.status == RequirementStatus.UNKNOWN.value
    assert req.verification_status == VerificationStatus.UNKNOWN.value


def test_requirement_provenance_record_created(db_session):
    case, pkg = _make_case_and_package(db_session)
    req = requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="ATTACHMENT_REQUIRED", description="Annexure B required",
        source=RequirementSourceType.USER_PROVIDED_CHECKLIST.value,
        source_reference="checklist item 2",
    )
    prov = db_session.query(models.ProvenanceRecord).filter(
        models.ProvenanceRecord.entity_id == req.id
    ).first()
    assert prov is not None
    assert prov.entity_type == "Requirement"


def test_requirement_every_row_has_required_fields(db_session):
    case, pkg = _make_case_and_package(db_session)
    req = requirement_engine.create_requirement(
        db_session, case_id=case.id, filing_package_id=pkg.id,
        requirement_type="REFERENCE_REQUIRED", description="Annexure C must be present",
        source=RequirementSourceType.SOURCE_DOCUMENT.value, source_reference="Petition.pdf",
        target_reference_label="Annexure C",
    )
    assert req.id and req.case_id and req.created_at and req.updated_at
    assert req.source == RequirementSourceType.SOURCE_DOCUMENT.value
    assert req.version == 1
