"""
Document ingestion (sec 7/8/35).

Security: filenames are sanitized (no path separators, no traversal),
content is hashed, and uploaded content is NEVER treated as instructions
(see security/prompt_injection.py for the guard applied before any
extracted text reaches an LLM prompt).

OCR: only plain-text-like files get real extraction in this build. Image
and scanned-PDF OCR is NOT implemented (no OCR engine bundled) and is
honestly reported as OCR_NOT_AVAILABLE rather than faked.
"""
import hashlib
import os
import re

TEXT_LIKE_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


def safe_filename(original: str) -> str:
    base = os.path.basename(original)
    base = re.sub(r"[^A-Za-z0-9_.\-]", "_", base)
    return base[:200] or "unnamed_file"


def extract_text(file_bytes: bytes, filename: str) -> tuple[str | None, str, str]:
    """Returns (extracted_text_or_None, extraction_method, ocr_status)."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in TEXT_LIKE_EXTENSIONS:
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            return text, "direct_text_decode", "NOT_APPLICABLE"
        except Exception:
            return None, "direct_text_decode_failed", "OCR_NOT_AVAILABLE"
    # PDFs / images: no OCR engine bundled in this build
    return None, "NOT_IMPLEMENTED", "OCR_NOT_AVAILABLE"


def content_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
