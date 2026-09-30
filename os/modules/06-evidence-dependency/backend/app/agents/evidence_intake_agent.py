"""
Evidence Intake Agent.

Responsible for confirming a document is safely ingested and ready for
extraction. It does not parse content itself (see document_service) and
it does not have authority to mark a document verified -- it only
reports structured intake status.
"""
from sqlalchemy.orm import Session

from app.models.orm import Document


def check_intake(db: Session, document_id: str) -> dict:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return {"ok": False, "reason": "Document not found."}
    if doc.status != "INGESTED":
        return {"ok": False, "reason": f"Document status is '{doc.status}', not INGESTED."}
    return {
        "ok": True,
        "document_id": doc.id,
        "sha256": doc.sha256_hash,
        "document_type": doc.document_type,
        "file_size_bytes": doc.file_size_bytes,
    }
