"""
Version / Supersession Engine.

Tracks relationships between document versions (SUPERSEDES,
SUPERSEDED_BY, REVISION_OF, DUPLICATE_OF, UNKNOWN_RELATIONSHIP). Never
deletes a historical version — "replacing" a document means uploading a
new DocumentVersion and recording a Supersession row; the old version
row is untouched and remains queryable (this is what the Time Machine
relies on).

Marking one version as superseding another always requires
confirmed_by_human=True to actually change which version is "current" on
the Document row — an automatic guess (e.g. from the duplicate engine)
is recorded but does not, by itself, change Document.current_version_id.
"""
from sqlalchemy.orm import Session
from app import models
from app.core.ids import new_id, utcnow
from app.core.enums import VersionRelationship


def propose_supersession(
    db: Session, *, case_id: str, predecessor_version_id: str, successor_version_id: str,
) -> models.Supersession:
    """Record a *proposed* supersession relationship (e.g. inferred from a
    duplicate group or explicit new-version upload). Does not change
    Document.current_version_id — see confirm_supersession()."""
    sup = models.Supersession(
        id=new_id("sup"), case_id=case_id,
        predecessor_document_version_id=predecessor_version_id,
        successor_document_version_id=successor_version_id,
        relationship_type=VersionRelationship.SUPERSEDES.value,
        confirmed_by_human=False,
        created_at=utcnow().isoformat(),
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)
    return sup


def confirm_supersession(db: Session, *, supersession_id: str) -> models.Supersession:
    """Human-approved: the successor version becomes the Document's
    current_version_id, and the predecessor's parent Document (if the
    same Document) has its status implicitly unaffected — only the
    pointer moves. If predecessor/successor belong to different Document
    rows (e.g. a resubmitted document uploaded as a fresh Document),
    the predecessor Document is marked SUPERSEDED."""
    sup = db.query(models.Supersession).filter(models.Supersession.id == supersession_id).first()
    if not sup:
        raise ValueError("Supersession not found")

    sup.confirmed_by_human = True

    successor_version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.id == sup.successor_document_version_id
    ).first()
    predecessor_version = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.id == sup.predecessor_document_version_id
    ).first()

    if successor_version:
        successor_doc = db.query(models.Document).filter(models.Document.id == successor_version.document_id).first()
        if successor_doc:
            successor_doc.current_version_id = successor_version.id
            successor_doc.updated_at = utcnow().isoformat()

    if predecessor_version and successor_version and predecessor_version.document_id != successor_version.document_id:
        predecessor_doc = db.query(models.Document).filter(models.Document.id == predecessor_version.document_id).first()
        if predecessor_doc:
            predecessor_doc.status = "SUPERSEDED"
            predecessor_doc.updated_at = utcnow().isoformat()

    db.commit()
    db.refresh(sup)
    return sup


def get_version_history(db: Session, *, document_id: str) -> list[dict]:
    """CURRENT / PREVIOUS VERSION / diff-relevant metadata for every
    version of a document, ordered oldest to newest. Never deletes or
    hides a historical version."""
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        return []
    versions = db.query(models.DocumentVersion).filter(
        models.DocumentVersion.document_id == document_id
    ).order_by(models.DocumentVersion.version_number.asc()).all()

    history = []
    for v in versions:
        history.append({
            "version_id": v.id,
            "version_number": v.version_number,
            "is_current": v.id == document.current_version_id,
            "original_filename": v.original_filename,
            "sha256": v.sha256,
            "uploaded_at": v.uploaded_at,
            "extraction_status": v.extraction_status,
        })
    return history
