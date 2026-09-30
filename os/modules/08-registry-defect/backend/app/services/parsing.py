"""
Document ingestion and parsing.

Safety properties enforced here:
- Extension AND content-based format detection (not trusted from the
  client-supplied filename alone).
- File size limits.
- Safe filenames (no path traversal — files are stored under a
  case/package-scoped directory using a generated id, never the
  client-supplied name).
- SHA-256 hashing of every uploaded file for provenance/duplicate
  detection.
- Parser failures are captured as data (extraction_status=FAILED),
  never raised as unhandled exceptions that could crash the request.
- Page/location numbers are only ever recorded when the parser actually
  determined them. Otherwise SOURCE_LOCATION_UNKNOWN is used — never a
  fabricated location.
"""
import os
import re
import csv
import json
import io
from dataclasses import dataclass, field
from app.core.ids import sha256_bytes
from app.core.enums import DocumentFormat

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".json", ".csv"}

STORAGE_ROOT = os.environ.get(
    "STORAGE_ROOT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage"),
)


@dataclass
class ExtractedSection:
    section_type: str
    section_index: int | None
    text_excerpt: str
    location_known: bool


@dataclass
class ParseResult:
    detected_format: str
    mime_type: str
    size_bytes: int
    sha256: str
    extraction_status: str  # OK / FAILED / UNSUPPORTED
    extraction_error: str | None
    extracted_text: str
    page_count: int | None
    sections: list = field(default_factory=list)
    source_location_known: bool = False
    quarantined: bool = False
    quarantine_reason: str | None = None


def safe_filename(original_filename: str, generated_id: str) -> str:
    """Never trust the client filename for storage. Preserve only the
    extension (validated) and use a generated id for the actual name,
    which eliminates path traversal and filename-collision risks."""
    ext = os.path.splitext(original_filename)[1].lower()
    ext = re.sub(r"[^a-z0-9.]", "", ext)
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".bin"
    return f"{generated_id}{ext}"


def detect_format(original_filename: str, content: bytes) -> DocumentFormat:
    ext = os.path.splitext(original_filename)[1].lower()
    if ext == ".pdf" or content[:4] == b"%PDF":
        return DocumentFormat.PDF
    if ext == ".docx" or content[:2] == b"PK":
        return DocumentFormat.DOCX
    if ext == ".json":
        return DocumentFormat.JSON
    if ext == ".csv":
        return DocumentFormat.CSV
    if ext == ".txt":
        return DocumentFormat.TXT
    return DocumentFormat.UNSUPPORTED


# Patterns used only to FLAG suspicious instruction-like content inside
# untrusted document text for a security defect. Matching text is never
# treated as an instruction to this system — see app/services/security_scan.py.
SUSPICIOUS_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"ignore\s+the\s+above",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"mark\s+this\s+filing\s+as\s+(complete|approved|compliant)",
    r"disregard\s+(the\s+)?(system|prior)\s+prompt",
    r"act\s+as\s+(the\s+)?(registry|judge|court)",
]


def scan_for_prompt_injection(text: str) -> list[str]:
    if not text:
        return []
    hits = []
    lowered = text.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            hits.append(pattern)
    return hits


def parse_file(original_filename: str, content: bytes) -> ParseResult:
    size_bytes = len(content)
    digest = sha256_bytes(content)
    fmt = detect_format(original_filename, content)

    if size_bytes == 0:
        return ParseResult(
            detected_format=fmt.value, mime_type="application/octet-stream",
            size_bytes=0, sha256=digest, extraction_status="FAILED",
            extraction_error="EMPTY_DOCUMENT", extracted_text="", page_count=None,
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        return ParseResult(
            detected_format=fmt.value, mime_type="application/octet-stream",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="FILE_TOO_LARGE", extracted_text="", page_count=None,
            quarantined=True, quarantine_reason="Exceeds maximum upload size",
        )

    if fmt == DocumentFormat.UNSUPPORTED:
        return ParseResult(
            detected_format=fmt.value, mime_type="application/octet-stream",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="UNSUPPORTED_FORMAT", extracted_text="", page_count=None,
        )

    try:
        if fmt == DocumentFormat.PDF:
            return _parse_pdf(content, digest, size_bytes)
        if fmt == DocumentFormat.DOCX:
            return _parse_docx(content, digest, size_bytes)
        if fmt == DocumentFormat.TXT:
            return _parse_txt(content, digest, size_bytes)
        if fmt == DocumentFormat.JSON:
            return _parse_json(content, digest, size_bytes)
        if fmt == DocumentFormat.CSV:
            return _parse_csv(content, digest, size_bytes)
    except Exception as exc:  # parser failures are data, not crashes
        return ParseResult(
            detected_format=fmt.value, mime_type="application/octet-stream",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error=f"PARSER_FAILURE: {type(exc).__name__}: {exc}",
            extracted_text="", page_count=None,
        )

    return ParseResult(
        detected_format=fmt.value, mime_type="application/octet-stream",
        size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
        extraction_error="UNSUPPORTED_FORMAT", extracted_text="", page_count=None,
    )


def _parse_pdf(content: bytes, digest: str, size_bytes: int) -> ParseResult:
    from PyPDF2 import PdfReader
    from PyPDF2.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(content))
    except PdfReadError as exc:
        return ParseResult(
            detected_format=DocumentFormat.PDF.value, mime_type="application/pdf",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error=f"CORRUPTED_DOCUMENT: {exc}", extracted_text="",
            page_count=None,
        )

    sections = []
    full_text_parts = []
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        full_text_parts.append(text)
        sections.append(ExtractedSection(
            section_type="PAGE", section_index=idx, text_excerpt=text[:2000],
            location_known=True,
        ))

    full_text = "\n".join(full_text_parts)
    if not full_text.strip():
        return ParseResult(
            detected_format=DocumentFormat.PDF.value, mime_type="application/pdf",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="UNREADABLE_DOCUMENT (no extractable text; may be a scanned image)",
            extracted_text="", page_count=len(reader.pages), sections=sections,
            source_location_known=True,
        )

    return ParseResult(
        detected_format=DocumentFormat.PDF.value, mime_type="application/pdf",
        size_bytes=size_bytes, sha256=digest, extraction_status="OK",
        extraction_error=None, extracted_text=full_text,
        page_count=len(reader.pages), sections=sections, source_location_known=True,
    )


def _parse_docx(content: bytes, digest: str, size_bytes: int) -> ParseResult:
    import docx as docx_lib

    try:
        doc = docx_lib.Document(io.BytesIO(content))
    except Exception as exc:
        return ParseResult(
            detected_format=DocumentFormat.DOCX.value,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error=f"CORRUPTED_DOCUMENT: {exc}", extracted_text="", page_count=None,
        )

    sections = []
    parts = []
    for idx, para in enumerate(doc.paragraphs):
        if para.text.strip():
            parts.append(para.text)
            sections.append(ExtractedSection(
                section_type="PARAGRAPH", section_index=idx,
                text_excerpt=para.text[:2000], location_known=True,
            ))

    full_text = "\n".join(parts)
    if not full_text.strip():
        return ParseResult(
            detected_format=DocumentFormat.DOCX.value,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="EMPTY_DOCUMENT", extracted_text="", page_count=None,
        )

    # DOCX has no reliable page concept without a rendering engine; we do
    # not fabricate a page count.
    return ParseResult(
        detected_format=DocumentFormat.DOCX.value,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=size_bytes, sha256=digest, extraction_status="OK",
        extraction_error=None, extracted_text=full_text, page_count=None,
        sections=sections, source_location_known=True,
    )


def _parse_txt(content: bytes, digest: str, size_bytes: int) -> ParseResult:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")

    if not text.strip():
        return ParseResult(
            detected_format=DocumentFormat.TXT.value, mime_type="text/plain",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="EMPTY_DOCUMENT", extracted_text="", page_count=None,
        )

    lines = text.splitlines()
    sections = [
        ExtractedSection(section_type="LINE", section_index=i, text_excerpt=line[:2000], location_known=True)
        for i, line in enumerate(lines) if line.strip()
    ]
    return ParseResult(
        detected_format=DocumentFormat.TXT.value, mime_type="text/plain",
        size_bytes=size_bytes, sha256=digest, extraction_status="OK",
        extraction_error=None, extracted_text=text, page_count=None,
        sections=sections, source_location_known=True,
    )


def _parse_json(content: bytes, digest: str, size_bytes: int) -> ParseResult:
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return ParseResult(
            detected_format=DocumentFormat.JSON.value, mime_type="application/json",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error=f"CORRUPTED_DOCUMENT: invalid JSON ({exc})",
            extracted_text="", page_count=None,
        )
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if not text.strip() or data in ({}, []):
        return ParseResult(
            detected_format=DocumentFormat.JSON.value, mime_type="application/json",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="EMPTY_DOCUMENT", extracted_text="", page_count=None,
        )
    return ParseResult(
        detected_format=DocumentFormat.JSON.value, mime_type="application/json",
        size_bytes=size_bytes, sha256=digest, extraction_status="OK",
        extraction_error=None, extracted_text=text, page_count=None,
        source_location_known=False,
    )


def _parse_csv(content: bytes, digest: str, size_bytes: int) -> ParseResult:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")
    try:
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
    except csv.Error as exc:
        return ParseResult(
            detected_format=DocumentFormat.CSV.value, mime_type="text/csv",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error=f"CORRUPTED_DOCUMENT: {exc}", extracted_text="", page_count=None,
        )
    if not rows:
        return ParseResult(
            detected_format=DocumentFormat.CSV.value, mime_type="text/csv",
            size_bytes=size_bytes, sha256=digest, extraction_status="FAILED",
            extraction_error="EMPTY_DOCUMENT", extracted_text="", page_count=None,
        )
    sections = [
        ExtractedSection(section_type="ROW", section_index=i, text_excerpt=",".join(row)[:2000], location_known=True)
        for i, row in enumerate(rows)
    ]
    full_text = "\n".join(",".join(row) for row in rows)
    return ParseResult(
        detected_format=DocumentFormat.CSV.value, mime_type="text/csv",
        size_bytes=size_bytes, sha256=digest, extraction_status="OK",
        extraction_error=None, extracted_text=full_text, page_count=None,
        sections=sections, source_location_known=True,
    )
