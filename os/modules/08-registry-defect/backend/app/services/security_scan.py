"""
Security scanning for ingested documents.

Uploaded documents are untrusted data. This module only ever produces
DEFECT records flagging suspicious content — it never allows document
content to alter control flow, requirement status, or defect status
elsewhere in the system. That separation is the actual defense; this
scanner is a detector/reporter, not a gate that executes instructions.
"""
from app.services.parsing import scan_for_prompt_injection

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".sh", ".cmd", ".com", ".scr", ".js", ".vbs", ".ps1", ".jar",
}


def check_dangerous_extension(filename: str) -> bool:
    lowered = filename.lower()
    return any(lowered.endswith(ext) for ext in DANGEROUS_EXTENSIONS)


def scan_text_for_injection(text: str) -> list[str]:
    """Returns the list of suspicious pattern matches found (for defect
    evidence). This is purely diagnostic — callers must not branch
    application behavior based on the *content* of what's returned,
    only on whether the list is non-empty (to raise a security defect)."""
    return scan_for_prompt_injection(text)
