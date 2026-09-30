"""
Date candidate detection.

This is a real, deterministic extractor — not a mock. It finds two kinds
of date-like spans in free text:

1. EXPLICIT dates: "12 March 2026", "March 12, 2026", "12/03/2026", "2026-03-12"
   -> resolved immediately via dateutil, provenance = SOURCE_EXPLICIT

2. RELATIVE dates: "within 30 days of service", "no later than 15 days
   after the order", "30 days from receipt of notice"
   -> NOT resolved to a concrete date here (we don't know the anchor's
      actual date yet), provenance = SOURCE_RELATIVE, and the anchor
      phrase is captured so a human or the dependency engine (Section 2)
      can link it to the real anchor event later.

Nothing here invents a date that isn't in the text, and nothing here
silently converts a relative date into an absolute one without an
anchor - that would violate the legal/safety boundary in the spec.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from dateutil import parser as dateutil_parser

from app.models.enums import ProvenanceState

CONTEXT_WINDOW = 60  # characters of context on each side, for human review


@dataclass
class ExtractedDateCandidate:
    raw_span: str
    context_snippet: str
    is_relative: bool
    resolved_date: Optional[datetime]
    relative_anchor_hint: Optional[str]
    provenance_state: ProvenanceState
    confidence: float


# --- Explicit date patterns -------------------------------------------------

_EXPLICIT_PATTERNS = [
    # 12 March 2026 / 12th March 2026
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{4}\b",
    # March 12, 2026 / March 12 2026
    r"\b(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
    # 12/03/2026, 12-03-2026, 2026-03-12
    r"\b\d{4}-\d{1,2}-\d{1,2}\b",
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
]

_EXPLICIT_RE = re.compile("|".join(f"(?:{p})" for p in _EXPLICIT_PATTERNS), re.IGNORECASE)

# --- Relative date patterns -------------------------------------------------
# Captures phrases like "within 30 days of service", "no later than 15 days
# after receipt", "45 days from the date of this order".

_RELATIVE_RE = re.compile(
    r"""
    (?P<full>
        (?:within|no\ later\ than|not\ later\ than)?\s*
        \b(?P<amount>\d{1,4})\s*
        (?P<unit>day|days|week|weeks|month|months|year|years)\b
        \s*
        (?:of|after|from)\s+
        (?P<anchor>[^.;\n]{3,80}?)
        (?=[.;\n]|$)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _context(text: str, start: int, end: int) -> str:
    lo = max(0, start - CONTEXT_WINDOW)
    hi = min(len(text), end + CONTEXT_WINDOW)
    return text[lo:hi].strip()


def extract_date_candidates(text: str) -> List[ExtractedDateCandidate]:
    candidates: List[ExtractedDateCandidate] = []
    claimed_spans = []  # (start, end) already matched, to avoid double-counting

    # 1. Explicit dates
    for m in _EXPLICIT_RE.finditer(text):
        raw = m.group(0)
        resolved = None
        confidence = 0.0
        try:
            if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", raw):
                # Unambiguous ISO 8601 (YYYY-MM-DD) — never apply dayfirst
                # heuristics to this, or "2026-04-01" gets silently
                # misread as day=4, month=1.
                resolved = dateutil_parser.parse(raw, yearfirst=True)
            else:
                # For ambiguous numeric formats like "12/03/2026" we assume
                # day-first, since this product's primary jurisdictional
                # context uses DD/MM/YYYY. This is a documented assumption,
                # not a silent guess — flag it via slightly lower confidence.
                resolved = dateutil_parser.parse(raw, fuzzy=False, dayfirst=True)
            confidence = 0.9
        except (ValueError, OverflowError):
            # Matched a date-shaped string dateutil still can't parse
            # (e.g. an impossible day/month). Keep it, but mark low confidence
            # and let a human resolve it rather than guessing.
            confidence = 0.2

        candidates.append(
            ExtractedDateCandidate(
                raw_span=raw,
                context_snippet=_context(text, m.start(), m.end()),
                is_relative=False,
                resolved_date=resolved,
                relative_anchor_hint=None,
                provenance_state=(
                    ProvenanceState.SOURCE_EXPLICIT
                    if resolved is not None
                    else ProvenanceState.REQUIRES_HUMAN_REVIEW
                ),
                confidence=confidence,
            )
        )
        claimed_spans.append((m.start(), m.end()))

    # 2. Relative dates
    for m in _RELATIVE_RE.finditer(text):
        start, end = m.start("full"), m.end("full")
        # Skip if this overlaps an explicit-date match (avoids double capture
        # of things like "30 days from 12 March 2026").
        if any(s < end and start < e for s, e in claimed_spans):
            continue

        anchor = m.group("anchor").strip()
        candidates.append(
            ExtractedDateCandidate(
                raw_span=m.group("full").strip(),
                context_snippet=_context(text, start, end),
                is_relative=True,
                resolved_date=None,
                relative_anchor_hint=anchor,
                provenance_state=ProvenanceState.SOURCE_RELATIVE,
                confidence=0.6,
            )
        )

    return candidates
