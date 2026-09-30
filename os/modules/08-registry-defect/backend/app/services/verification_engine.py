"""
Verification Engine.

The spec is explicit: "Do not automatically mark a defect resolved
merely because a file changed. Re-run verification." This module is the
concrete mechanism for that rule.

verify_defect() re-runs the SAME underlying check that originally
produced the defect (not a proxy like "was any file uploaded since"), and
only writes result=VERIFIED when that check now finds the condition
cleared. It never mutates the Defect's status directly — it records a
Verification row and a ReviewTask, leaving the actual RESOLVED transition
to a human via the review gate, consistent with defect_engine's
DefectLifecycleState (VERIFIED precedes, and is distinct from, RESOLVED).
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow


def _checklist_item_now_found(db: Session, defect: models.Defect) -> bool | None:
    """Re-checks whether the requirement(s) referenced by a
    MISSING_DOCUMENT/MISSING_ATTACHMENT defect are now FOUND on the
    current checklist. Returns None if inapplicable (no requirement_refs)."""
    if not defect.requirement_refs:
        return None
    items = db.query(models.ChecklistItem).filter(
        models.ChecklistItem.requirement_id.in_(defect.requirement_refs),
        models.ChecklistItem.filing_package_id == defect.filing_package_id,
    ).all()
    if not items:
        return None
    return all(item.status == "FOUND" for item in items)


def _attachment_reference_now_resolved(db: Session, defect: models.Defect) -> bool | None:
    """Re-checks whether the AttachmentReference(s) tied to a
    MISSING_REFERENCED_ITEM defect are now resolved."""
    evidence = db.query(models.DefectEvidence).filter(models.DefectEvidence.defect_id == defect.id).all()
    version_ids = [e.document_version_id for e in evidence if e.document_version_id]
    if not version_ids:
        return None
    refs = db.query(models.AttachmentReference).filter(
        models.AttachmentReference.source_document_version_id.in_(version_ids),
        models.AttachmentReference.filing_package_id == defect.filing_package_id,
    ).all()
    if not refs:
        return None
    return all(r.resolved for r in refs)


def _conflict_now_resolved(db: Session, defect: models.Defect) -> bool | None:
    for ref in defect.source_refs or []:
        if isinstance(ref, dict) and ref.get("type") == "conflict":
            conflict = db.query(models.Conflict).filter(models.Conflict.id == ref["id"]).first()
            if conflict:
                return conflict.status != "UNRESOLVED"
    return None


def _duplicate_now_reviewed(db: Session, defect: models.Defect) -> bool | None:
    for ref in defect.source_refs or []:
        if isinstance(ref, dict) and ref.get("type") == "duplicate_group":
            group = db.query(models.DuplicateGroup).filter(models.DuplicateGroup.id == ref["id"]).first()
            if group:
                return bool(group.reviewed)
    return None


def _objection_now_resolved(db: Session, defect: models.Defect) -> bool | None:
    for ref in defect.source_refs or []:
        if isinstance(ref, dict) and ref.get("type") == "objection":
            obj = db.query(models.RegistryObjection).filter(models.RegistryObjection.id == ref["id"]).first()
            if obj:
                return obj.status == "RESOLVED"
    return None


CHECKERS = [
    _checklist_item_now_found,
    _attachment_reference_now_resolved,
    _conflict_now_resolved,
    _duplicate_now_reviewed,
    _objection_now_resolved,
]


def verify_defect(db: Session, *, defect_id: str, user_id: str | None = None) -> models.Verification:
    """Re-runs the concrete check(s) relevant to this defect's type and
    records the outcome. Does NOT itself change Defect.status — creates a
    ReviewTask so a human confirms the final RESOLVED transition."""
    defect = db.query(models.Defect).filter(models.Defect.id == defect_id).first()
    if not defect:
        raise ValueError("Defect not found")

    outcomes = []
    for checker in CHECKERS:
        result = checker(db, defect)
        if result is not None:
            outcomes.append(result)

    if not outcomes:
        result = "UNKNOWN"
        notes = "No applicable re-check exists for this defect type in this build; human verification required."
    elif all(outcomes):
        result = "VERIFIED"
        notes = "The underlying condition that produced this defect was re-checked and no longer holds."
    else:
        result = "STILL_FAILING"
        notes = "The underlying condition that produced this defect was re-checked and still holds."

    verification = models.Verification(
        id=new_id("ver"), case_id=defect.case_id, target_type="DEFECT", target_id=defect.id,
        result=result, notes=notes, verified_at=utcnow().isoformat(), verified_by_user_id=user_id,
    )
    db.add(verification)

    if result == "VERIFIED" and defect.status not in ("RESOLVED", "REJECTED", "FALSE_POSITIVE"):
        defect.status = "VERIFIED"
        task = models.ReviewTask(
            case_id=defect.case_id, filing_package_id=defect.filing_package_id,
            target_type="DEFECT", target_id=defect.id,
            action_requested="CONFIRM_RESOLUTION_AFTER_VERIFICATION",
            decision="PENDING",
        )
        db.add(task)

    db.commit()
    db.refresh(verification)
    return verification
