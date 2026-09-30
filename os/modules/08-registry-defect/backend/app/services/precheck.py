"""
Precheck Orchestrator.

Runs the full non-destructive detection pipeline for a filing package:
  1. Rebuild attachment reference resolution
  2. Rebuild checklist against current requirements/documents
  3. Detect metadata conflicts
  4. Detect duplicates
  5. Generate defects from all of the above, plus document quality,
     security scan, and open objections
  6. Advance the filing package lifecycle state (never past
     REVIEW_REQUIRED / READY_FOR_HUMAN_REVIEW automatically — later
     states require an explicit human-approved review task)

This does not delete existing CONFIRMED/RESOLVED defects; it clears and
regenerates only DETECTED-state defects produced by the automated
agents, so a human's prior triage decisions are preserved.
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import utcnow
from app.services import (
    attachment_engine, checklist_engine, metadata_engine,
    duplicate_engine, defect_engine,
)


def run_precheck(db: Session, *, case_id: str, filing_package_id: str) -> dict:
    # Clear system-detected, still-untouched defects before regenerating,
    # so re-running precheck doesn't pile up duplicates. Anything a human
    # has already moved past DETECTED (triaged, confirmed, rejected, etc.)
    # is preserved untouched.
    db.query(models.Defect).filter(
        models.Defect.filing_package_id == filing_package_id,
        models.Defect.status == "DETECTED",
    ).delete()
    db.commit()

    attachment_engine.resolve_references(db, filing_package_id=filing_package_id)
    checklist_engine.build_checklist(db, case_id=case_id, filing_package_id=filing_package_id)
    metadata_engine.detect_metadata_conflicts(db, case_id=case_id, filing_package_id=filing_package_id)
    duplicate_engine.detect_duplicates(db, case_id=case_id, filing_package_id=filing_package_id)

    new_defects = []
    new_defects += defect_engine.generate_defects_from_checklist(db, case_id=case_id, filing_package_id=filing_package_id)
    new_defects += defect_engine.generate_defects_from_attachment_references(db, case_id=case_id, filing_package_id=filing_package_id)
    new_defects += defect_engine.generate_defects_from_conflicts(db, case_id=case_id, filing_package_id=filing_package_id)
    new_defects += defect_engine.generate_defects_from_duplicates(db, case_id=case_id, filing_package_id=filing_package_id)
    new_defects += defect_engine.generate_defects_from_document_quality(db, case_id=case_id, filing_package_id=filing_package_id)
    new_defects += defect_engine.generate_defects_from_security_scan(db, case_id=case_id, filing_package_id=filing_package_id)
    new_defects += defect_engine.generate_defects_from_objections(db, case_id=case_id, filing_package_id=filing_package_id)

    package = db.query(models.FilingPackage).filter(models.FilingPackage.id == filing_package_id).first()
    open_defects = db.query(models.Defect).filter(
        models.Defect.filing_package_id == filing_package_id,
        models.Defect.status.notin_(["RESOLVED", "REJECTED", "FALSE_POSITIVE"]),
    ).count()

    if open_defects > 0:
        package.lifecycle_state = "REVIEW_REQUIRED"
    else:
        package.lifecycle_state = "READY_FOR_HUMAN_REVIEW"
    package.updated_at = utcnow().isoformat()
    db.commit()

    # Create review tasks for every newly detected defect that requires
    # human review (all of them, by construction of the Defect model).
    for d in new_defects:
        task = models.ReviewTask(
            case_id=case_id, filing_package_id=filing_package_id,
            target_type="DEFECT", target_id=d.id,
            action_requested="CONFIRM_OR_REJECT_DEFECT",
            decision="PENDING",
        )
        db.add(task)
    db.commit()

    return {
        "filing_package_id": filing_package_id,
        "new_defect_count": len(new_defects),
        "open_defect_count": open_defects,
        "lifecycle_state": package.lifecycle_state,
    }
