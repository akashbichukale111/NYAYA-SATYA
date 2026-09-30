from app.services.date_extraction import extract_date_candidates
from app.models.enums import ProvenanceState


def test_explicit_date_is_resolved():
    text = "The hearing is scheduled for 12 March 2026 at the district court."
    candidates = extract_date_candidates(text)
    explicit = [c for c in candidates if not c.is_relative]
    assert len(explicit) == 1
    assert explicit[0].resolved_date is not None
    assert explicit[0].resolved_date.year == 2026
    assert explicit[0].resolved_date.month == 3
    assert explicit[0].resolved_date.day == 12
    assert explicit[0].provenance_state == ProvenanceState.SOURCE_EXPLICIT


def test_explicit_date_alternate_format():
    text = "Payment is due by 2026-04-01 without exception."
    candidates = extract_date_candidates(text)
    explicit = [c for c in candidates if not c.is_relative]
    assert len(explicit) == 1
    assert explicit[0].resolved_date.month == 4
    assert explicit[0].resolved_date.day == 1


def test_relative_date_is_not_falsely_resolved():
    text = "The respondent must file a reply within 30 days of service of this notice."
    candidates = extract_date_candidates(text)
    relative = [c for c in candidates if c.is_relative]
    assert len(relative) == 1
    r = relative[0]
    assert r.resolved_date is None, "Relative dates must never be silently resolved"
    assert "30" in r.raw_span
    assert r.relative_anchor_hint is not None
    assert "service" in r.relative_anchor_hint.lower()
    assert r.provenance_state == ProvenanceState.SOURCE_RELATIVE


def test_no_dates_found_returns_empty_list():
    text = "This paragraph contains no dates of any kind whatsoever."
    candidates = extract_date_candidates(text)
    assert candidates == []


def test_multiple_dates_in_one_document():
    text = (
        "This order is dated 1 January 2026. "
        "An appeal must be filed within 15 days after receipt of this order. "
        "The next hearing is set for March 5, 2026."
    )
    candidates = extract_date_candidates(text)
    assert len(candidates) == 3
    explicit_count = sum(1 for c in candidates if not c.is_relative)
    relative_count = sum(1 for c in candidates if c.is_relative)
    assert explicit_count == 2
    assert relative_count == 1


def test_explicit_and_relative_do_not_overlap_falsely():
    # "30 days from 12 March 2026" should not double count the explicit date
    # as also being a relative anchor match target incorrectly overlapping.
    text = "Compliance is required 30 days from 12 March 2026."
    candidates = extract_date_candidates(text)
    # Should find the explicit date; relative regex requires 'of/after/from'
    # followed by an anchor phrase, and here the anchor IS the explicit date,
    # so no separate unresolved relative candidate with a bogus anchor should
    # be created for the same span.
    explicit = [c for c in candidates if not c.is_relative]
    assert len(explicit) == 1
