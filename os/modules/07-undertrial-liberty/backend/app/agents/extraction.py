"""
Extraction agents.

Each agent scans document text for keyword patterns associated with a
specific event vocabulary and produces STRUCTURED, PROVENANCE-LINKED
candidate events. Agents never infer an event that isn't textually
supported, and always attach the matching sentence as source_text_snippet
plus the document id as source_document_id.

Because DEMO mode must run without any external API key, these agents are
implemented as deterministic keyword/regex matchers rather than LLM calls.
When a real LLM_PROVIDER is configured, the same structured-output contract
applies -- see app/core/llm.py -- but extraction agents in this build use
the rule-based path uniformly so behavior is reproducible and auditable,
which matters for a system whose outputs feed human legal review.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.agents.date_parser import classify_and_extract_date
from app.core.enums import (
    CustodyEventType, HearingStatus, OrderStatus, BailEventType,
    ReleaseEventType, ExtractionMethod, DateType,
)


def _sentences(text: str) -> List[str]:
    # Simple, safe sentence splitter -- text is untrusted data, treated only as string content.
    raw = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [s.strip() for s in raw if s.strip()]


@dataclass
class ExtractedCandidate:
    kind: str
    fields: dict
    source_text_snippet: str
    date_iso: Optional[str] = None
    date_type: str = DateType.UNKNOWN_DATE.value


CUSTODY_KEYWORDS = {
    CustodyEventType.ARREST_RECORDED: [r"\barrest(ed)?\b"],
    CustodyEventType.REMAND_ORDER: [r"\bremand(ed)?\b"],
    CustodyEventType.CUSTODY_EXTENDED: [r"\bcustody\s+extend", r"\bextension of custody\b"],
    CustodyEventType.JUDICIAL_CUSTODY: [r"\bjudicial custody\b"],
    CustodyEventType.POLICE_CUSTODY: [r"\bpolice custody\b"],
    CustodyEventType.TRANSFER: [r"\btransferred?\s+to\b"],
    CustodyEventType.PRODUCTION: [r"\bproduced before\b", r"\bproduction warrant\b"],
    CustodyEventType.COURT_APPEARANCE: [r"\bappeared before\b", r"\bappearance before the court\b"],
    CustodyEventType.RELEASE_ORDER_RECORDED: [r"\brelease order\b"],
    CustodyEventType.RELEASE_RECORDED: [r"\breleased from custody\b", r"\bwas released\b"],
    CustodyEventType.CUSTODY_STATUS_UPDATED: [r"\bcustody status\b"],
}

HEARING_KEYWORDS = [r"\bhearing\b", r"\bnext date\b", r"\blisted on\b", r"\bposted for\b"]
HEARING_RESULT_KEYWORDS = [r"\border (?:passed|issued)\b", r"\bdisposed\b", r"\badjourned\b"]

ORDER_KEYWORDS = {
    OrderStatus.ORDER_ISSUED: [r"\border (?:is )?(?:issued|passed|granted)\b"],
    OrderStatus.ORDER_MODIFIED: [r"\border (?:is )?modified\b", r"\border (?:is )?amended\b"],
    OrderStatus.ORDER_CLARIFIED: [r"\border (?:is )?clarified\b"],
    OrderStatus.ORDER_SUPERSEDED: [r"\border (?:is )?superseded\b", r"\border (?:is )?set aside\b"],
}

BAIL_KEYWORDS = {
    BailEventType.BAIL_APPLICATION_RECORDED: [r"\bbail application (?:filed|recorded)\b", r"\bapplication for bail\b"],
    BailEventType.BAIL_HEARING_SCHEDULED: [r"\bbail hearing\b"],
    BailEventType.BAIL_ORDER_RECORDED: [r"\bbail order\b", r"\bbail (?:is )?granted\b", r"\bbail (?:is )?rejected\b",
                                         r"\bbail (?:is )?denied\b"],
    BailEventType.BAIL_APPLICATION_WITHDRAWN: [r"\bbail application withdrawn\b"],
    BailEventType.BAIL_APPLICATION_DISPOSED: [r"\bbail application disposed\b"],
}

RELEASE_KEYWORDS = {
    ReleaseEventType.RELEASE_ORDER_RECORDED: [r"\brelease order (?:passed|issued|recorded)\b"],
    ReleaseEventType.RELEASE_DOCUMENT_RECEIVED: [r"\brelease document received\b", r"\brelease warrant received\b"],
    ReleaseEventType.RELEASE_EVENT_REPORTED: [r"\breported (?:to have been )?released\b", r"\bfamily reports release\b"],
}


class CustodyEventExtractionAgent:
    name = "custody_event_extraction_agent"

    def extract(self, document_id: str, text: str) -> List[ExtractedCandidate]:
        candidates = []
        for sentence in _sentences(text):
            for event_type, patterns in CUSTODY_KEYWORDS.items():
                if any(re.search(p, sentence, re.I) for p in patterns):
                    date_iso, date_type, _ = classify_and_extract_date(sentence)
                    candidates.append(ExtractedCandidate(
                        kind="custody_event",
                        fields={"event_type": event_type.value, "source_document_id": document_id},
                        source_text_snippet=sentence[:500],
                        date_iso=date_iso,
                        date_type=date_type,
                    ))
        return candidates


class CourtEventAgent:
    name = "court_event_agent"

    def extract(self, document_id: str, text: str) -> List[ExtractedCandidate]:
        candidates = []
        for sentence in _sentences(text):
            if any(re.search(p, sentence, re.I) for p in HEARING_KEYWORDS):
                date_iso, date_type, _ = classify_and_extract_date(sentence)
                has_result = any(re.search(p, sentence, re.I) for p in HEARING_RESULT_KEYWORDS)
                status = HearingStatus.HELD_RESULT_RECORDED.value if has_result else HearingStatus.SCHEDULED.value
                candidates.append(ExtractedCandidate(
                    kind="hearing",
                    fields={
                        "status": status,
                        "purpose": sentence[:200],
                        "source_document_id": document_id,
                    },
                    source_text_snippet=sentence[:500],
                    date_iso=date_iso,
                    date_type=date_type,
                ))
        return candidates


class OrderExtractionAgent:
    name = "order_extraction_agent"

    def extract(self, document_id: str, text: str) -> List[ExtractedCandidate]:
        candidates = []
        for sentence in _sentences(text):
            for status, patterns in ORDER_KEYWORDS.items():
                if any(re.search(p, sentence, re.I) for p in patterns):
                    date_iso, date_type, _ = classify_and_extract_date(sentence)
                    candidates.append(ExtractedCandidate(
                        kind="order",
                        fields={
                            "status": status.value,
                            "summary": sentence[:300],
                            "source_document_id": document_id,
                        },
                        source_text_snippet=sentence[:500],
                        date_iso=date_iso,
                        date_type=date_type,
                    ))
        return candidates


class BailEventAgent:
    name = "bail_event_agent"

    def extract(self, document_id: str, text: str) -> List[ExtractedCandidate]:
        candidates = []
        for sentence in _sentences(text):
            for event_type, patterns in BAIL_KEYWORDS.items():
                if any(re.search(p, sentence, re.I) for p in patterns):
                    date_iso, date_type, _ = classify_and_extract_date(sentence)
                    candidates.append(ExtractedCandidate(
                        kind="bail_event",
                        fields={
                            "event_type": event_type.value,
                            "summary": sentence[:300],
                            "source_document_id": document_id,
                        },
                        source_text_snippet=sentence[:500],
                        date_iso=date_iso,
                        date_type=date_type,
                    ))
        return candidates


class ReleaseEventAgent:
    """
    Tracks release-related records WITHOUT assuming current status.
    current_status_confidence is set conservatively -- see enums.CurrentStatusConfidence.
    A reported release is UNVERIFIED until a human reviewer confirms it.
    """
    name = "release_event_agent"

    def extract(self, document_id: str, text: str) -> List[ExtractedCandidate]:
        candidates = []
        for sentence in _sentences(text):
            for event_type, patterns in RELEASE_KEYWORDS.items():
                if any(re.search(p, sentence, re.I) for p in patterns):
                    date_iso, date_type, _ = classify_and_extract_date(sentence)
                    candidates.append(ExtractedCandidate(
                        kind="release_event",
                        fields={
                            "event_type": event_type.value,
                            "summary": sentence[:300],
                            "source_document_id": document_id,
                        },
                        source_text_snippet=sentence[:500],
                        date_iso=date_iso,
                        date_type=date_type,
                    ))
        return candidates


class DocumentIntakeAgent:
    """Orchestrates all extraction agents over one ingested document's text."""
    name = "document_intake_agent"

    def __init__(self):
        self.custody_agent = CustodyEventExtractionAgent()
        self.court_agent = CourtEventAgent()
        self.order_agent = OrderExtractionAgent()
        self.bail_agent = BailEventAgent()
        self.release_agent = ReleaseEventAgent()

    def process(self, document_id: str, text: str) -> dict:
        return {
            "custody_events": self.custody_agent.extract(document_id, text),
            "hearings": self.court_agent.extract(document_id, text),
            "orders": self.order_agent.extract(document_id, text),
            "bail_events": self.bail_agent.extract(document_id, text),
            "release_events": self.release_agent.extract(document_id, text),
        }
