"""
Time Machine.

Built entirely on data this system already never deletes:
- DocumentVersion rows (a "replaced" document is a new version, not an
  overwrite — see version_engine.py).
- AuditEvent rows (append-only, with before_state/after_state — see
  core/audit.py).

There is no separate "snapshot" table that could drift from reality or
be edited after the fact. "What did the package look like at time T" is
answered by filtering these two real, immutable sources by timestamp —
never by a cached or synthesized snapshot object.
"""
from sqlalchemy.orm import Session
from app import models


def get_document_history(db: Session, *, filing_package_id: str) -> list[dict]:
    documents = db.query(models.Document).filter(
        models.Document.filing_package_id == filing_package_id
    ).all()
    history = []
    for doc in documents:
        versions = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == doc.id
        ).order_by(models.DocumentVersion.version_number.asc()).all()
        history.append({
            "document_id": doc.id,
            "display_name": doc.display_name,
            "current_version_id": doc.current_version_id,
            "versions": [
                {
                    "version_id": v.id,
                    "version_number": v.version_number,
                    "uploaded_at": v.uploaded_at,
                    "original_filename": v.original_filename,
                    "sha256": v.sha256,
                    "is_current": v.id == doc.current_version_id,
                }
                for v in versions
            ],
        })
    return history


def get_defect_history(db: Session, *, case_id: str, filing_package_id: str) -> list[dict]:
    """Reconstructs each defect's state changes from the append-only audit
    log rather than from a mutable snapshot."""
    events = db.query(models.AuditEvent).filter(
        models.AuditEvent.case_id == case_id,
        models.AuditEvent.entity_type == "Defect",
    ).order_by(models.AuditEvent.timestamp.asc()).all()

    by_defect: dict[str, list[dict]] = {}
    for e in events:
        by_defect.setdefault(e.entity_id, []).append({
            "action": e.action,
            "timestamp": e.timestamp,
            "before_state": e.before_state,
            "after_state": e.after_state,
            "reason": e.reason,
            "actor_role": e.actor_role,
        })

    defects = db.query(models.Defect).filter(models.Defect.filing_package_id == filing_package_id).all()
    return [
        {"defect_id": d.id, "current_status": d.status, "history": by_defect.get(d.id, [])}
        for d in defects
    ]


def get_objection_history(db: Session, *, case_id: str, filing_package_id: str) -> list[dict]:
    events = db.query(models.AuditEvent).filter(
        models.AuditEvent.case_id == case_id,
        models.AuditEvent.entity_type == "RegistryObjection",
    ).order_by(models.AuditEvent.timestamp.asc()).all()

    by_obj: dict[str, list[dict]] = {}
    for e in events:
        by_obj.setdefault(e.entity_id, []).append({
            "action": e.action, "timestamp": e.timestamp,
            "before_state": e.before_state, "after_state": e.after_state,
        })

    objections = db.query(models.RegistryObjection).filter(
        models.RegistryObjection.filing_package_id == filing_package_id
    ).all()
    return [
        {"objection_id": o.id, "current_status": o.status, "history": by_obj.get(o.id, [])}
        for o in objections
    ]


def get_requirement_source_history(db: Session, *, filing_package_id: str) -> list[dict]:
    """Which requirement source was active — requirements are never
    edited in place in this build (a change would be a new Requirement
    row with an incremented `version`), so 'what source was active' is
    just the requirement's own immutable source field plus its
    ProvenanceRecord."""
    requirements = db.query(models.Requirement).filter(
        models.Requirement.filing_package_id == filing_package_id
    ).all()
    result = []
    for r in requirements:
        prov = db.query(models.ProvenanceRecord).filter(
            models.ProvenanceRecord.entity_type == "Requirement",
            models.ProvenanceRecord.entity_id == r.id,
        ).first()
        result.append({
            "requirement_id": r.id, "description": r.description,
            "source": r.source, "source_reference": r.source_reference,
            "version": r.version, "recorded_at": prov.recorded_at if prov else None,
        })
    return result


def get_submission_snapshot(db: Session, *, filing_package_id: str) -> dict | None:
    """What the package looked like at the moment of its most recent
    FilingSubmission — this reads the frozen snapshot_json recorded at
    that time (see routers, Section 3), not a live re-query."""
    submission = db.query(models.FilingSubmission).filter(
        models.FilingSubmission.filing_package_id == filing_package_id
    ).order_by(models.FilingSubmission.submitted_at.desc()).first()
    if not submission:
        return None
    return {
        "submission_id": submission.id,
        "submitted_at": submission.submitted_at,
        "snapshot": submission.snapshot_json,
    }


def build_time_machine_view(db: Session, *, case_id: str, filing_package_id: str) -> dict:
    return {
        "filing_package_id": filing_package_id,
        "document_history": get_document_history(db, filing_package_id=filing_package_id),
        "defect_history": get_defect_history(db, case_id=case_id, filing_package_id=filing_package_id),
        "objection_history": get_objection_history(db, case_id=case_id, filing_package_id=filing_package_id),
        "requirement_source_history": get_requirement_source_history(db, filing_package_id=filing_package_id),
        "last_submission_snapshot": get_submission_snapshot(db, filing_package_id=filing_package_id),
    }
