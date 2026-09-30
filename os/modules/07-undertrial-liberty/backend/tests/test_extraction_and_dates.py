import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.date_parser import classify_and_extract_date
from app.core.enums import DateType


def test_explicit_date_recognized():
    date_iso, date_type, snippet = classify_and_extract_date("Next hearing on 14 October 2026.")
    assert date_iso == "2026-10-14"
    assert date_type == DateType.SOURCE_EXPLICIT_DATE.value


def test_relative_date_recognized():
    date_iso, date_type, snippet = classify_and_extract_date("Compliance is required within 10 days.")
    assert date_iso is not None
    assert date_type == DateType.SOURCE_RELATIVE_DATE.value


def test_no_date_never_fabricated():
    date_iso, date_type, snippet = classify_and_extract_date("The matter is pending further information.")
    assert date_iso is None
    assert date_type == DateType.UNKNOWN_DATE.value


def test_extraction_agents_only_match_known_vocabulary():
    from app.agents.extraction import DocumentIntakeAgent
    from app.core.enums import CustodyEventType
    agent = DocumentIntakeAgent()
    text = "The accused was arrested on 1 January 2026. Bail application filed on 3 January 2026."
    result = agent.process("doc1", text)
    valid_types = {t.value for t in CustodyEventType}
    for c in result["custody_events"]:
        assert c.fields["event_type"] in valid_types


def test_extraction_never_infers_unstated_event():
    from app.agents.extraction import DocumentIntakeAgent
    agent = DocumentIntakeAgent()
    # No custody keywords at all -- must extract nothing.
    text = "The weather was clear on the day of the hearing."
    result = agent.process("doc1", text)
    assert result["custody_events"] == []
