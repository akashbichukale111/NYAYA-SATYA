"""
Document ingestion pipeline.

Every uploaded document is treated as untrusted data (see docs/security.md):
its bytes are validated (size/extension/MIME), hashed, saved under a
case-scoped directory with a generated safe filename (never the
user-supplied name), and only then parsed. Anything that fails validation
is quarantined, never parsed, and never silently accepted.
"""
import csv
import hashlib
import io
import json
import os
import uuid
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.orm import Document, EvidenceItem

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
QUARANTINE_DIR = os.environ.get("QUARANTINE_DIR", "./quarantine")
MAX_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))

ALLOWED_EXTENSIONS = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".txt": "TXT",
    ".json": "JSON",
    ".csv": "CSV",
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/json",
    "text/csv",
    "application/octet-stream",  # some browsers/clients send this for any binary; extension is authoritative
}


class DocumentValidationError(Exception):
    def __init__(self, reason: str, quarantine: bool = True):
        self.reason = reason
        self.quarantine = quarantine
        super().__init__(reason)


def _safe_filename(original_filename: str) -> str:
    """Strip any path component and unsafe characters; the on-disk name is
    always <uuid>__<sanitized-basename>, never the raw user-supplied path."""
    base = os.path.basename(original_filename or "upload")
    base = base.replace("\x00", "")
    safe = "".join(c for c in base if c.isalnum() or c in ("-", "_", "."))
    safe = safe[-120:] or "upload"
    return f"{uuid.uuid4().hex}__{safe}"


def _resolve_within(base_dir: str, filename: str) -> str:
    """Build a path and verify it cannot escape base_dir (path traversal guard)."""
    os.makedirs(base_dir, exist_ok=True)
    base_real = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base_dir, filename))
    if not candidate.startswith(base_real + os.sep) and candidate != base_real:
        raise DocumentValidationError("Resolved path escapes the storage directory.", quarantine=False)
    return candidate


def validate_and_store(
    db: Session,
    case_id: str,
    original_filename: str,
    content: bytes,
    mime_type: str,
) -> Document:
    """
    Validate an upload and persist it. On any validation failure, the file
    (if any bytes were readable) is written to QUARANTINE_DIR and a Document
    row is created with status QUARANTINED plus a reason -- nothing is
    silently dropped, and nothing unsafe is parsed.
    """
    ext = os.path.splitext(original_filename or "")[1].lower()
    size = len(content)
    safe_name = _safe_filename(original_filename)

    reasons = []
    if size == 0:
        reasons.append("Empty file.")
    if size > MAX_UPLOAD_SIZE_BYTES:
        reasons.append(f"File exceeds max size of {MAX_UPLOAD_SIZE_BYTES} bytes.")
    if ext not in ALLOWED_EXTENSIONS:
        reasons.append(f"Unsupported file extension '{ext}'. Allowed: {list(ALLOWED_EXTENSIONS)}.")
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        reasons.append(f"Unsupported MIME type '{mime_type}'.")

    sha256_hash = hashlib.sha256(content).hexdigest()

    if reasons:
        quarantine_path = _resolve_within(os.path.join(QUARANTINE_DIR, case_id), safe_name)
        with open(quarantine_path, "wb") as f:
            f.write(content)
        doc = Document(
            case_id=case_id, filename=original_filename or "upload",
            stored_path=quarantine_path, mime_type=mime_type,
            file_size_bytes=size, sha256_hash=sha256_hash,
            document_type=ALLOWED_EXTENSIONS.get(ext, "UNKNOWN"),
            extraction_method="NONE", status="QUARANTINED",
        )
        db.add(doc)
        db.flush()
        from app.services.review_service import log_audit_event
        log_audit_event(
            db, case_id, actor="DocumentIntakeAgent", actor_type="AGENT",
            action="DOCUMENT_QUARANTINED", target_type="DOCUMENT", target_id=doc.id,
            detail={"reasons": reasons},
        )
        db.commit()
        db.refresh(doc)
        raise DocumentValidationError("; ".join(reasons))

    doc_type = ALLOWED_EXTENSIONS[ext]
    dest_path = _resolve_within(os.path.join(UPLOAD_DIR, case_id), safe_name)
    with open(dest_path, "wb") as f:
        f.write(content)

    doc = Document(
        case_id=case_id, filename=original_filename, stored_path=dest_path,
        mime_type=mime_type, file_size_bytes=size, sha256_hash=sha256_hash,
        document_type=doc_type, extraction_method="UPLOAD", status="INGESTED",
    )
    db.add(doc)
    db.flush()
    from app.services.review_service import log_audit_event
    log_audit_event(
        db, case_id, actor="DocumentIntakeAgent", actor_type="AGENT",
        action="DOCUMENT_INGESTED", target_type="DOCUMENT", target_id=doc.id,
        detail={"sha256": sha256_hash, "size_bytes": size, "document_type": doc_type},
    )
    db.commit()
    db.refresh(doc)
    return doc


def parse_document(doc: Document) -> Tuple[str, List[Dict]]:
    """
    Parse a stored, already-validated document into (full_text, page_chunks).
    page_chunks is a list of {"page_number": int|None, "text": str} -- real
    page numbers only where the format actually supports them (PDF). Parsing
    errors are raised as DocumentValidationError(quarantine=False) so the
    caller can mark the document PARSE_FAILED without deleting it.
    """
    try:
        with open(doc.stored_path, "rb") as f:
            raw = f.read()

        if doc.document_type == "TXT":
            text = raw.decode("utf-8", errors="replace")
            return text, [{"page_number": None, "text": text}]

        if doc.document_type == "JSON":
            data = json.loads(raw.decode("utf-8", errors="replace"))
            text = json.dumps(data, indent=2, ensure_ascii=False)
            return text, [{"page_number": None, "text": text}]

        if doc.document_type == "CSV":
            text_io = io.StringIO(raw.decode("utf-8", errors="replace"))
            reader = csv.reader(text_io)
            rows = list(reader)
            text = "\n".join(", ".join(row) for row in rows)
            return text, [{"page_number": None, "text": text}]

        if doc.document_type == "PDF":
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(raw))
            chunks = []
            full_text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                chunks.append({"page_number": i + 1, "text": page_text})
                full_text_parts.append(page_text)
            return "\n".join(full_text_parts), chunks

        if doc.document_type == "DOCX":
            import docx
            d = docx.Document(io.BytesIO(raw))
            paragraphs = [p.text for p in d.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            return text, [{"page_number": None, "text": text}]

        raise DocumentValidationError(f"No parser for document type '{doc.document_type}'.", quarantine=False)

    except DocumentValidationError:
        raise
    except Exception as e:  # noqa: BLE001 -- deliberately broad: any parser failure must be caught and reported, never crash the request
        raise DocumentValidationError(f"Parse error: {e}", quarantine=False)
