"""
Secure document ingestion.

Uploaded documents are UNTRUSTED DATA. Nothing extracted from them is
executed as an instruction. Text content is stored and later scanned by
extraction agents purely as data to pattern-match against known event
vocabularies -- never interpreted as commands to this system.
"""
import hashlib
import io
import os
import re
import uuid
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.core.enums import DocumentStatus, ExtractionMethod

QUARANTINE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "_quarantine")
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "_storage")
os.makedirs(QUARANTINE_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)


@dataclass
class IngestResult:
    safe_filename: str
    sha256: str
    size_bytes: int
    status: str
    extraction_method: Optional[str]
    extracted_text: Optional[str]
    rejection_reason: Optional[str]


def _safe_filename(original_filename: str) -> str:
    """
    Strips path components and disallowed characters to prevent path
    traversal (e.g. '../../etc/passwd') and unsafe filesystem writes.
    """
    base = os.path.basename(original_filename)
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    if not base or base in (".", ".."):
        base = "unnamed_file"
    unique_prefix = uuid.uuid4().hex[:10]
    return f"{unique_prefix}_{base}"


def _extension_of(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    return ext


def _extract_text(safe_path: str, ext: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (extracted_text, extraction_method). Never raises on parse issues;
    returns (None, None) instead so the caller can mark PARSE_FAILED."""
    try:
        if ext == ".txt":
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), ExtractionMethod.PLAIN_TEXT.value
        if ext == ".json":
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), ExtractionMethod.JSON_STRUCTURED.value
        if ext == ".csv":
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(), ExtractionMethod.CSV_STRUCTURED.value
        if ext == ".pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(safe_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts), ExtractionMethod.PDF_TEXT_EXTRACTION.value
        if ext == ".docx":
            import docx
            d = docx.Document(safe_path)
            text_parts = [p.text for p in d.paragraphs]
            return "\n".join(text_parts), ExtractionMethod.DOCX_TEXT_EXTRACTION.value
    except Exception:
        return None, None
    return None, None


def ingest_document(file_bytes: bytes, original_filename: str, mime_type: str) -> IngestResult:
    size = len(file_bytes)
    ext = _extension_of(original_filename)
    safe_name = _safe_filename(original_filename)
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # --- Validation gates ---
    if size == 0:
        return IngestResult(safe_name, sha256, size, DocumentStatus.REJECTED.value, None, None,
                             "File is empty.")
    if size > settings.MAX_UPLOAD_BYTES:
        return IngestResult(safe_name, sha256, size, DocumentStatus.REJECTED.value, None, None,
                             f"File exceeds max upload size of {settings.MAX_UPLOAD_BYTES} bytes.")
    if ext not in settings.ALLOWED_EXTENSIONS:
        return IngestResult(safe_name, sha256, size, DocumentStatus.REJECTED.value, None, None,
                             f"Extension '{ext}' is not permitted.")
    if mime_type not in settings.ALLOWED_MIME_TYPES:
        # Quarantine rather than silently accept a mismatched MIME type.
        quarantine_path = os.path.join(QUARANTINE_DIR, safe_name)
        with open(quarantine_path, "wb") as f:
            f.write(file_bytes)
        return IngestResult(safe_name, sha256, size, DocumentStatus.QUARANTINED.value, None, None,
                             f"MIME type '{mime_type}' did not match an allowed type; file quarantined.")

    # --- Path traversal protection: always write under STORAGE_DIR using the sanitized name ---
    safe_path = os.path.abspath(os.path.join(STORAGE_DIR, safe_name))
    if not safe_path.startswith(os.path.abspath(STORAGE_DIR)):
        return IngestResult(safe_name, sha256, size, DocumentStatus.REJECTED.value, None, None,
                             "Resolved path escaped storage directory.")

    with open(safe_path, "wb") as f:
        f.write(file_bytes)

    text, method = _extract_text(safe_path, ext)
    if text is None:
        return IngestResult(safe_name, sha256, size, DocumentStatus.PARSE_FAILED.value, None, None,
                             "Parser could not extract text from this file.")

    return IngestResult(safe_name, sha256, size, DocumentStatus.PARSED.value, method, text, None)
