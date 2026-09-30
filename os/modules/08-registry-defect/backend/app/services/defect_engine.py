"""
Defect Engine.

Turns findings from the other engines (checklist, attachment reference,
metadata, duplicate, document quality, security scan) into structured
Defect rows with linked DefectEvidence. Severity here means operational
attention only, never a legal-consequence judgment (enforced by the
fixed description templates below, which never claim rejection,
invalidity, or an outcome).
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow
from app.core.enums import DefectType, DefectSeverity, DEFECT_CATEGORY_MAP


def _create_defect(
    db: Session, *, case_id: str, filing_package_id: str, defect_type: DefectType,
    severity: DefectSeverity, description: str, source_refs: list, document_refs: list,
    requirement_refs: list, detected_by: str, evidence: list[dict] | None = None,
) -> models.Defect:
    defect = models.Defect(
        id=new_id("dft"),
        case_id=case_id,
        filing_package_id=filing_package_id,
        defect_type=defect_type.value,
        category=DEFECT_CATEGORY_MAP[defect_type],
        severity=severity.value,
        status="DETECTED",
        description=description,
        source_refs=source_refs,
        document_refs=document_refs,
        requirement_refs=requirement_refs,
        detected_by=detected_by,
        detected_at=utcnow().isoformat(),
        verification_status="SYSTEM_DETECTED",
        human_review_required=True,
    )
    db.add(defect)
    db.commit()
    db.refresh(defect)

    for ev in (evidence or []):
        record = models.DefectEvidence(
            id=new_id("evid"), case_id=case_id, defect_id=defect.id,
            document_version_id=ev.get("document_version_id"),
            section_id=ev.get("section_id"),
            requirement_id=ev.get("requirement_id"),
            excerpt=ev.get("excerpt"),
            location_known=ev.get("location_known", False),
            location_label=ev.get("location_label"),
        )
        db.add(record)
    db.commit()
    return defect


def generate_defects_from_checklist(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    defects = []
    items = db.query(models.ChecklistItem).filter(
        models.ChecklistItem.filing_package_id == filing_package_id
    ).all()
    for item in items:
        req = db.query(models.Requirement).filter(models.Requirement.id == item.requirement_id).first()
        if item.status == "MISSING":
            label = req.target_reference_label or req.description if req else "unspecified item"
            defect = _create_defect(
                db, case_id=case_id, filing_package_id=filing_package_id,
                defect_type=DefectType.MISSING_DOCUMENT if (req and req.requirement_type == "DOCUMENT_REQUIRED") else DefectType.MISSING_ATTACHMENT,
                severity=DefectSeverity.HIGH_ATTENTION,
                description=f"The applicable filing checklist requires '{label}', but it was not found in this package.",
                source_refs=[{"type": "requirement", "id": req.id, "source": req.source}] if req else [],
                document_refs=[],
                requirement_refs=[req.id] if req else [],
                detected_by="ChecklistAgent",
            )
            defects.append(defect)
        elif item.status == "REQUIRES_HUMAN_REVIEW":
            defect = _create_defect(
                db, case_id=case_id, filing_package_id=filing_package_id,
                defect_type=DefectType.PROVENANCE_GAP,
                severity=DefectSeverity.REQUIRES_HUMAN_REVIEW,
                description="A checklist item could not be automatically resolved and requires human verification of its requirement source.",
                source_refs=[{"type": "requirement", "id": req.id}] if req else [],
                document_refs=[], requirement_refs=[req.id] if req else [],
                detected_by="ChecklistAgent",
            )
            defects.append(defect)
    return defects


def generate_defects_from_attachment_references(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    defects = []
    refs = db.query(models.AttachmentReference).filter(
        models.AttachmentReference.filing_package_id == filing_package_id,
        models.AttachmentReference.resolved == False,  # noqa: E712
    ).all()
    for ref in refs:
        section = db.query(models.DocumentSection).filter(models.DocumentSection.id == ref.section_id).first() if ref.section_id else None
        location_label = None
        if section and section.location_known and section.section_type == "PAGE" and section.section_index is not None:
            location_label = f"page {section.section_index + 1}"
        description = (
            f"The submitted document references '{ref.reference_label}', but no corresponding "
            f"file was detected in this filing package."
        )
        defect = _create_defect(
            db, case_id=case_id, filing_package_id=filing_package_id,
            defect_type=DefectType.MISSING_REFERENCED_ITEM,
            severity=DefectSeverity.HIGH_ATTENTION,
            description=description,
            source_refs=[{"type": "document_version", "id": ref.source_document_version_id}],
            document_refs=[], requirement_refs=[],
            detected_by="AttachmentReferenceAgent",
            evidence=[{
                "document_version_id": ref.source_document_version_id,
                "section_id": ref.section_id,
                "excerpt": ref.raw_context,
                "location_known": bool(location_label),
                "location_label": location_label,
            }],
        )
        defects.append(defect)
    return defects


def generate_defects_from_conflicts(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    defects = []
    conflicts = db.query(models.Conflict).filter(
        models.Conflict.filing_package_id == filing_package_id,
        models.Conflict.status == "UNRESOLVED",
    ).all()
    for conflict in conflicts:
        defect_type = {
            "case_number": DefectType.IDENTIFIER_MISMATCH,
            "reference_number": DefectType.IDENTIFIER_MISMATCH,
            "party_name": DefectType.PARTY_NAME_CONFLICT,
            "document_date": DefectType.DATE_CONFLICT,
            "order_date": DefectType.DATE_CONFLICT,
            "filing_date": DefectType.DATE_CONFLICT,
        }.get(conflict.field_name, DefectType.METADATA_CONFLICT)

        description = (
            f"Documents in this package report inconsistent values for '{conflict.field_name}': "
            f"'{conflict.left_value}' vs '{conflict.right_value}'. The system does not determine "
            f"which value is correct; human review is required."
        )
        defect = _create_defect(
            db, case_id=case_id, filing_package_id=filing_package_id,
            defect_type=defect_type,
            severity=DefectSeverity.REQUIRES_HUMAN_REVIEW,
            description=description,
            source_refs=[{"type": "conflict", "id": conflict.id}],
            document_refs=[v for v in [conflict.left_document_version_id, conflict.right_document_version_id] if v],
            requirement_refs=[],
            detected_by="MetadataAgent",
        )
        defects.append(defect)
    return defects


def generate_defects_from_duplicates(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    defects = []
    groups = db.query(models.DuplicateGroup).filter(
        models.DuplicateGroup.filing_package_id == filing_package_id,
        models.DuplicateGroup.reviewed == False,  # noqa: E712
    ).all()
    for group in groups:
        defect_type = DefectType.DUPLICATE_VERSION if group.duplicate_type == "HASH_DUPLICATE" else DefectType.VERSION_AMBIGUITY
        description = (
            f"The system detected a possible duplicate: {group.similarity_evidence}. "
            f"{len(group.member_document_version_ids)} document version(s) are involved. "
            f"Human review is required to confirm which, if any, should be treated as the current version."
        )
        defect = _create_defect(
            db, case_id=case_id, filing_package_id=filing_package_id,
            defect_type=defect_type,
            severity=DefectSeverity.ATTENTION,
            description=description,
            source_refs=[{"type": "duplicate_group", "id": group.id}],
            document_refs=group.member_document_version_ids,
            requirement_refs=[],
            detected_by="DuplicateAgent",
        )
        defects.append(defect)
    return defects


def generate_defects_from_document_quality(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    defects = []
    versions = (
        db.query(models.DocumentVersion)
        .join(models.Document, models.DocumentVersion.document_id == models.Document.id)
        .filter(
            models.DocumentVersion.case_id == case_id,
            models.Document.filing_package_id == filing_package_id,
            models.DocumentVersion.extraction_status == "FAILED",
        )
        .all()
    )
    for v in versions:
        error = v.extraction_error or ""
        if "EMPTY_DOCUMENT" in error:
            dtype = DefectType.EMPTY
        elif "CORRUPTED" in error:
            dtype = DefectType.CORRUPTED
        elif "UNSUPPORTED_FORMAT" in error:
            dtype = DefectType.UNSUPPORTED_FORMAT
        elif "UNREADABLE" in error:
            dtype = DefectType.UNREADABLE
        else:
            dtype = DefectType.PARSER_FAILURE

        defect = _create_defect(
            db, case_id=case_id, filing_package_id=filing_package_id,
            defect_type=dtype,
            severity=DefectSeverity.ATTENTION,
            description=f"Document '{v.original_filename}' could not be processed: {error}",
            source_refs=[{"type": "document_version", "id": v.id}],
            document_refs=[v.document_id],
            requirement_refs=[],
            detected_by="DocumentQualityAgent",
        )
        defects.append(defect)

        if not v.sha256:
            hash_defect = _create_defect(
                db, case_id=case_id, filing_package_id=filing_package_id,
                defect_type=DefectType.HASH_MISSING,
                severity=DefectSeverity.INFO,
                description=f"Document '{v.original_filename}' has no recorded content hash; provenance cannot be fully established.",
                source_refs=[{"type": "document_version", "id": v.id}],
                document_refs=[v.document_id],
                requirement_refs=[],
                detected_by="AuditAgent",
            )
            defects.append(hash_defect)
    return defects


def generate_defects_from_security_scan(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    from app.services.security_scan import scan_text_for_injection
    defects = []
    versions = (
        db.query(models.DocumentVersion)
        .join(models.Document, models.DocumentVersion.document_id == models.Document.id)
        .filter(
            models.DocumentVersion.case_id == case_id,
            models.Document.filing_package_id == filing_package_id,
            models.DocumentVersion.extraction_status == "OK",
        )
        .all()
    )
    for v in versions:
        hits = scan_text_for_injection(v.extracted_text or "")
        if hits:
            defect = _create_defect(
                db, case_id=case_id, filing_package_id=filing_package_id,
                defect_type=DefectType.PROMPT_INJECTION_CONTENT,
                severity=DefectSeverity.HIGH_ATTENTION,
                description=(
                    f"Document '{v.original_filename}' contains text patterns resembling an attempt "
                    f"to instruct an automated system, rather than ordinary filing content. This "
                    f"document's content has been treated strictly as data and has not affected any "
                    f"automated determination. Human review is required."
                ),
                source_refs=[{"type": "document_version", "id": v.id}],
                document_refs=[v.document_id],
                requirement_refs=[],
                detected_by="AuditAgent",
            )
            defects.append(defect)
    return defects


def generate_defects_from_objections(db: Session, *, case_id: str, filing_package_id: str) -> list[models.Defect]:
    defects = []
    objections = db.query(models.RegistryObjection).filter(
        models.RegistryObjection.filing_package_id == filing_package_id,
        models.RegistryObjection.status.in_(["OPEN", "ACKNOWLEDGED", "CORRECTION_PLANNED"]),
        models.RegistryObjection.linked_defect_id.is_(None),
    ).all()
    for obj in objections:
        defect = _create_defect(
            db, case_id=case_id, filing_package_id=filing_package_id,
            defect_type=DefectType.UNRESOLVED_OBJECTION,
            severity=DefectSeverity.HIGH_ATTENTION,
            description=f"An unresolved registry objection is recorded for this filing package: \"{obj.original_text[:200]}\"",
            source_refs=[{"type": "objection", "id": obj.id, "source": obj.source_reference}],
            document_refs=[], requirement_refs=[],
            detected_by="ObjectionAgent",
        )
        obj.linked_defect_id = defect.id
        db.commit()
        defects.append(defect)
    return defects
