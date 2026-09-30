"""
NYAYA-SATYA Integration Adapter.

Exposes a read-only operational summary for a case, matching the
contract in the master spec exactly. This is explicitly NOT a legal
compliance verdict — every field is a plain count or list of ids/labels
derived from data already in this database, with no synthesized legal
judgment. The module remains independently runnable: nothing here calls
out to any NYAYA-SATYA service, and this adapter can be deleted without
breaking the rest of the application.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, assert_case_access
from app.core.ids import utcnow
from app import models, schemas

router = APIRouter(tags=["nyaya-satya-integration"])


@router.get("/api/integration/nyaya-satya/cases/{case_id}/summary", response_model=schemas.NyayaSatyaSummary)
def get_case_summary(case_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    case = assert_case_access(db, user, case_id)

    packages = db.query(models.FilingPackage).filter(models.FilingPackage.case_id == case_id).all()
    package_ids = [p.id for p in packages]

    open_defects_q = db.query(models.Defect).filter(
        models.Defect.case_id == case_id,
        models.Defect.status.notin_(["RESOLVED", "REJECTED", "FALSE_POSITIVE"]),
    )
    open_defects = open_defects_q.all()
    high_attention = [d for d in open_defects if d.severity in ("HIGH_ATTENTION", "REQUIRES_HUMAN_REVIEW")]

    missing_documents = [
        {"defect_id": d.id, "description": d.description}
        for d in open_defects if d.defect_type == "MISSING_DOCUMENT"
    ]
    missing_references = [
        {"defect_id": d.id, "description": d.description}
        for d in open_defects if d.defect_type in ("MISSING_REFERENCED_ITEM", "BROKEN_ATTACHMENT_REFERENCE")
    ]
    metadata_conflicts = [
        {"conflict_id": c.id, "field": c.field_name}
        for c in db.query(models.Conflict).filter(
            models.Conflict.case_id == case_id, models.Conflict.status == "UNRESOLVED"
        ).all()
    ]
    duplicate_groups = [
        {"group_id": g.id, "type": g.duplicate_type}
        for g in db.query(models.DuplicateGroup).filter(
            models.DuplicateGroup.case_id == case_id, models.DuplicateGroup.reviewed == False  # noqa: E712
        ).all()
    ]
    open_objections = [
        {"objection_id": o.id, "status": o.status}
        for o in db.query(models.RegistryObjection).filter(
            models.RegistryObjection.case_id == case_id,
            models.RegistryObjection.status != "RESOLVED",
        ).all()
    ]
    corrections_pending = [
        {"correction_id": c.id, "status": c.status}
        for c in db.query(models.CorrectionRequest).filter(
            models.CorrectionRequest.case_id == case_id,
            models.CorrectionRequest.status != "RESOLVED",
        ).all()
    ]
    verification_pending = [
        {"verification_id": v.id, "target_type": v.target_type, "target_id": v.target_id}
        for v in db.query(models.Verification).filter(
            models.Verification.case_id == case_id, models.Verification.result == "PENDING"
        ).all()
    ]
    blocked_workflows = [p.id for p in packages if p.lifecycle_state in ("BLOCKED", "CONFLICTING", "UNKNOWN")]
    attention_items = [{"defect_id": d.id, "severity": d.severity, "type": d.defect_type} for d in high_attention]
    provenance_refs = [
        {"entity_type": p.entity_type, "entity_id": p.entity_id, "origin": p.origin}
        for p in db.query(models.ProvenanceRecord).filter(models.ProvenanceRecord.case_id == case_id).all()
    ]

    return schemas.NyayaSatyaSummary(
        case_id=case_id,
        filing_packages=len(packages),
        open_defects=len(open_defects),
        high_attention_defects=len(high_attention),
        missing_documents=missing_documents,
        missing_references=missing_references,
        metadata_conflicts=metadata_conflicts,
        duplicate_groups=duplicate_groups,
        open_objections=open_objections,
        corrections_pending=corrections_pending,
        verification_pending=verification_pending,
        blocked_workflows=blocked_workflows,
        attention_items=attention_items,
        provenance_refs=provenance_refs,
        last_updated=utcnow().isoformat(),
    )
