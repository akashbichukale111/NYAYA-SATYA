"""
Source-stated date parsing.

This module ONLY recognizes dates that are explicitly written in source
text. It never computes a date from a statutory period, holiday calendar,
or jurisdiction-specific rule. If no explicit or clearly-relative date
phrase is found, callers must treat the date as UNKNOWN_DATE.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from app.core.enums import DateType

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "14 October 2026", "14th October 2026", "October 14, 2026", "2026-10-14"
DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS.keys()) + r")\s+(\d{4})\b", re.I),
    re.compile(r"\b(" + "|".join(MONTHS.keys()) + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", re.I),
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
]

RELATIVE_PATTERNS = [
    (re.compile(r"\bnext\s+hearing\s+(?:is\s+)?(?:in|after)\s+(\d+)\s+days?\b", re.I), "days"),
    (re.compile(r"\bwithin\s+(\d+)\s+days?\b", re.I), "days"),
    (re.compile(r"\bwithin\s+(\d+)\s+weeks?\b", re.I), "weeks"),
]


def find_explicit_date(text: str) -> Optional[Tuple[str, str]]:
    """Returns (iso_date_string, matched_snippet) or None."""
    if not text:
        return None
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        groups = m.groups()
        try:
            if groups[0].isdigit() and len(groups[0]) == 4:
                # ISO form yyyy-mm-dd
                y, mo, d = int(groups[0]), int(groups[1]), int(groups[2])
            elif groups[0].isdigit():
                # "14 October 2026"
                d, mo_name, y = int(groups[0]), groups[1].lower(), int(groups[2])
                mo = MONTHS.get(mo_name)
            else:
                # "October 14, 2026"
                mo_name, d, y = groups[0].lower(), int(groups[1]), int(groups[2])
                mo = MONTHS.get(mo_name)
            if mo is None:
                continue
            dt = datetime(y, mo, d)
            return dt.date().isoformat(), m.group(0)
        except (ValueError, TypeError):
            continue
    return None


def find_relative_date(text: str, reference_date: Optional[datetime] = None) -> Optional[Tuple[str, str]]:
    """
    Recognizes an EXPLICITLY STATED relative phrase like 'within 10 days'
    and anchors it to a reference date (e.g. the document's own stated
    date, or ingestion date if none is available). This is not a statutory
    computation -- it is a literal translation of a relative phrase the
    source itself used.
    """
    if not text:
        return None
    ref = reference_date or datetime.now(timezone.utc)
    for pattern, unit in RELATIVE_PATTERNS:
        m = pattern.search(text)
        if m:
            n = int(m.group(1))
            delta = timedelta(days=n) if unit == "days" else timedelta(weeks=n)
            return (ref + delta).date().isoformat(), m.group(0)
    return None


def classify_and_extract_date(text: str) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Returns (date_iso_or_none, DateType, snippet_or_none).
    Never fabricates a date. Defaults to UNKNOWN_DATE.
    """
    explicit = find_explicit_date(text)
    if explicit:
        return explicit[0], DateType.SOURCE_EXPLICIT_DATE.value, explicit[1]
    relative = find_relative_date(text)
    if relative:
        return relative[0], DateType.SOURCE_RELATIVE_DATE.value, relative[1]
    return None, DateType.UNKNOWN_DATE.value, None
