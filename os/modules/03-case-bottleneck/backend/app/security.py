"""
Security layer (Section 41).

Scope note: this is a hackathon-grade implementation of the *pattern*
required by the spec — it is not a production content-security system.
It implements:
  - filename safety (no path traversal, extension allow-list)
  - a simple content hash for tamper-evidence
  - a heuristic prompt-injection scanner that QUARANTINES suspicious
    uploaded document content instead of ever treating it as an instruction

Any document flagged here is marked `contains_injection_attempt=True` and
`quarantined=True`. Quarantined documents are still stored (for audit /
forensics) but their content_text is EXCLUDED from anything the agents read
as case facts — they are only ever displayed back to a human reviewer,
verbatim, clearly labelled.
"""
import hashlib
import re
from pathlib import PurePosixPath

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".png", ".jpg", ".jpeg"}

# Heuristic patterns. Real-world defense-in-depth would combine this with
# an isolated extraction sandbox and an instruction-hierarchy-aware model;
# here we keep it simple, explainable, and testable.
INJECTION_PATTERNS = [
    r"ignore (all|any|previous|prior) instructions",
    r"disregard (all|any|previous|prior) instructions",
    r"you are now",
    r"system\s*:\s*",
    r"act as (the )?(admin|system|developer)",
    r"mark (all|this) bottleneck[s]? (as )?resolved",
    r"approve (this|all) action[s]?",
    r"reveal (the )?(system prompt|instructions)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def safe_filename(name: str) -> str:
    """Strip path components and reject traversal / unsafe characters."""
    p = PurePosixPath(name).name  # drops any directory component
    p = re.sub(r"[^A-Za-z0-9_.\-]", "_", p)
    if not p or p in (".", ".."):
        raise ValueError("Invalid filename")
    return p


def validate_extension(name: str) -> None:
    ext = PurePosixPath(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension {ext!r} not permitted")


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()


def scan_for_injection(content: str) -> bool:
    """Return True if the content contains a suspected prompt-injection attempt."""
    return any(pattern.search(content) for pattern in _COMPILED)
