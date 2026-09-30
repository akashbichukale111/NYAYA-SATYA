from app.services import attachment_engine


def test_extract_references_finds_annexure():
    text = "The identity document is attached as Annexure A. Also see Annexure B for the order copy."
    refs = attachment_engine.extract_references(text)
    labels = {r["label"] for r in refs}
    assert "Annexure A" in labels
    assert "Annexure B" in labels


def test_extract_references_deduplicates():
    text = "See Annexure A. Please refer again to Annexure A for details."
    refs = attachment_engine.extract_references(text)
    assert len(refs) == 1


def test_extract_references_handles_multiple_types():
    text = "Refer to Exhibit 1, Schedule B, and Appendix C for supporting material."
    refs = attachment_engine.extract_references(text)
    types = {r["reference_type"] for r in refs}
    assert types == {"EXHIBIT", "SCHEDULE", "APPENDIX"}


def test_extract_references_no_matches_on_plain_text():
    text = "This petition contains no cross references at all."
    refs = attachment_engine.extract_references(text)
    assert refs == []
