"""
Hearing Context Engine (section 5). Rule-based keyword matching against
ingested document text -- deliberately simple and auditable rather than
an opaque model call, so "HEARING CONTEXT UNCERTAIN" is a real, explainable
outcome and never silently guessed.
"""
from __future__ import annotations

PURPOSE_KEYWORDS = {
    "FRAMING_OF_CHARGES": ["framing of charge", "framing of charges"],
    "EVIDENCE_RECORDING": ["recording of evidence", "examination-in-chief", "cross-examination"],
    "ARGUMENTS": ["final arguments", "arguments on merits", "arguments heard"],
    "ADMISSION_DENIAL": ["admission and denial", "admission/denial", "admission or denial"],
    "CASE_MANAGEMENT": ["case management hearing", "scheduling of dates"],
    "BAIL_HEARING": ["bail application", "hearing on bail"],
    "MOTION_HEARING": ["hearing on the application", "interim application"],
}


def determine_purpose(document_texts: list[str], fixture_purpose: str | None = None) -> tuple[str | None, str, list[str]]:
    """Returns (purpose, status, uncertainty_reasons).

    If a fixture/docket already states the purpose explicitly (real systems
    would get this from a court e-filing feed), we trust it and mark
    DETERMINED. Otherwise we scan document text for known phrasing.
    """
    if fixture_purpose:
        return fixture_purpose, "DETERMINED", []

    combined = " \n".join((t or "").lower() for t in document_texts)
    if not combined.strip():
        return None, "UNCERTAIN", [
            "No documents have been ingested yet that reference the next hearing's purpose."
        ]

    for purpose, phrases in PURPOSE_KEYWORDS.items():
        for phrase in phrases:
            if phrase in combined:
                return purpose, "DETERMINED", []

    return None, "UNCERTAIN", [
        "No ingested document text matched a recognized hearing-purpose phrase.",
        "A human should confirm the purpose from the cause list or court order before proceeding.",
    ]
