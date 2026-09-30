"""
Requirement engine.

Core rule: the engine NEVER invents a requirement. Every Requirement row
must be created with an explicit `source` (RequirementSourceType) and,
where applicable, a `source_reference` pointing at what produced it
(a user checklist, an uploaded document, an imported requirement set,
or an explicitly configured registry rule). Requirements created by this
service always start with verification_status=UNVERIFIED or
REQUIRES_VERIFICATION unless the caller supplies source evidence — the
engine does not decide something is verified on its own say-so.
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow
from app.core.enums import RequirementSourceType, RequirementStatus, VerificationStatus


def create_requirement(
    db: Session,
    *,
    case_id: str,
    filing_package_id: str,
    requirement_type: str,
    description: str,
    source: str,
    source_reference: str | None = None,
    target_reference_label: str | None = None,
    jurisdiction: str | None = None,
    effective_from: str | None = None,
    effective_until: str | None = None,
) -> models.Requirement:
    if source == RequirementSourceType.UNKNOWN.value and not source_reference:
        verification_status = VerificationStatus.UNKNOWN.value
        status = RequirementStatus.UNKNOWN.value
    elif source in (
        RequirementSourceType.USER_PROVIDED_CHECKLIST.value,
        RequirementSourceType.SOURCE_DOCUMENT.value,
        RequirementSourceType.AUTHORIZED_TEMPLATE.value,
        RequirementSourceType.CONFIGURED_REGISTRY_RULE.value,
        RequirementSourceType.IMPORTED_REQUIREMENT_SET.value,
    ):
        verification_status = VerificationStatus.SOURCE_SUPPORTED.value
        status = RequirementStatus.ACTIVE.value
    else:
        verification_status = VerificationStatus.REQUIRES_HUMAN_REVIEW.value
        status = RequirementStatus.REQUIRES_VERIFICATION.value

    req = models.Requirement(
        id=new_id("req"),
        case_id=case_id,
        filing_package_id=filing_package_id,
        requirement_type=requirement_type,
        description=description,
        source=source,
        source_reference=source_reference,
        target_reference_label=target_reference_label,
        jurisdiction=jurisdiction,
        effective_from=effective_from,
        effective_until=effective_until,
        status=status,
        verification_status=verification_status,
        created_at=utcnow().isoformat(),
        updated_at=utcnow().isoformat(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    db.add(models.ProvenanceRecord(
        id=new_id("prov"), case_id=case_id, entity_type="Requirement", entity_id=req.id,
        origin="USER_INPUT" if source == RequirementSourceType.USER_PROVIDED_CHECKLIST.value else "IMPORTED",
        origin_detail=source_reference or "no source reference supplied",
    ))
    db.commit()
    return req


def mark_requirement_unknown(db: Session, requirement: models.Requirement, reason: str) -> models.Requirement:
    requirement.status = RequirementStatus.UNKNOWN.value
    requirement.verification_status = VerificationStatus.UNKNOWN.value
    requirement.updated_at = utcnow().isoformat()
    db.commit()
    db.refresh(requirement)
    return requirement
