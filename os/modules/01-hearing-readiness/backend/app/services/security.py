from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

from app.config import settings


class UploadRejected(Exception):
    pass


# --- File validation -------------------------------------------------

def validate_upload(filename: str, size_bytes: int) -> str:
    """Returns the lowercase extension if valid, else raises UploadRejected."""
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UploadRejected(f"File type '{ext}' is not allowed.")
    if size_bytes > settings.MAX_UPLOAD_BYTES:
        raise UploadRejected(
            f"File exceeds max size of {settings.MAX_UPLOAD_BYTES} bytes."
        )
    if size_bytes <= 0:
        raise UploadRejected("Empty file.")
    return ext


def safe_stored_path(ext: str) -> tuple[str, Path]:
    """Generates a random, non-guessable filename inside UPLOAD_DIR and
    guarantees (via resolve()) the resulting path cannot escape it -
    defends against path traversal even if a caller mishandles filenames."""
    stored_name = f"{uuid.uuid4().hex}{ext}"
    full_path = (settings.UPLOAD_DIR / stored_name).resolve()
    if settings.UPLOAD_DIR.resolve() not in full_path.parents:
        raise UploadRejected("Resolved path escapes upload directory.")
    return stored_name, full_path


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- Prompt-injection awareness ---------------------------------------
# Uploaded documents are UNTRUSTED DATA. We never pass extracted text to an
# LLM provider as a system/instruction role -- only ever as a clearly
# labeled data block (see llm_provider.py: wrap_untrusted_data()). This
# heuristic scan additionally flags documents that *contain* instruction-like
# language, purely so the UI can show the analyst a warning; it does not by
# itself change what the system does with the file.

_INJECTION_PATTERNS = [
    r"ignore (all |previous |the )*instructions",
    r"you are now",
    r"system prompt",
    r"disregard (all |previous )*instructions",
    r"act as (an?|the) (ai|assistant|judge|lawyer)",
    r"new instructions\s*:",
    r"override (your|the) (rules|policy|instructions)",
    r"do not (follow|apply) (the )?(safety|policy)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def scan_for_injection(text: str) -> list[str]:
    if not text:
        return []
    hits = sorted(set(m.group(0).lower() for m in _INJECTION_RE.finditer(text)))
    return hits


# --- Legal safety firewall (section 22) --------------------------------
# Blocks requests asking the system to step outside readiness/workflow
# support into judicial-decision territory.

_FORBIDDEN_INTENT_PATTERNS = [
    r"predict (the )?verdict",
    r"will (he|she|they|the accused|the defendant) (be found|be convicted|be acquitted|win|lose)",
    r"determine (guilt|innocence)",
    r"decide (the )?sentence",
    r"is (he|she|they) guilty",
    r"replace the judge",
    r"fabricate evidence",
    r"manipulate evidence",
    r"conceal evidence",
    r"create a deceptive filing",
    r"misrepresent the facts",
    r"hide (this|the) evidence",
]
_FORBIDDEN_RE = re.compile("|".join(_FORBIDDEN_INTENT_PATTERNS), re.IGNORECASE)


class ForbiddenIntent(Exception):
    def __init__(self, matched: str):
        self.matched = matched
        super().__init__(
            "This system is a hearing-readiness and workflow-assistance tool. "
            "It cannot predict judicial outcomes, determine guilt or innocence, "
            "or help fabricate, conceal, or misrepresent evidence. "
            f"(matched pattern: '{matched}')"
        )


def enforce_legal_safety_firewall(text: str) -> None:
    if not text:
        return
    m = _FORBIDDEN_RE.search(text)
    if m:
        raise ForbiddenIntent(m.group(0))
