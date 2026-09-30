import os

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_multipage.pdf")


def test_pdf_upload_and_process_preserves_real_page_numbers(client):
    """
    Anti-fabrication check specific to PDF: the fixture has three real pages,
    each with a distinct marker sentence. After upload + pipeline processing,
    every evidence item extracted from this document must carry the ACTUAL
    page number it came from (1, 2, or 3) -- never a guessed or default value,
    and never a page number for a format that doesn't support it.
    """
    case = client.post("/api/cases", json={"title": "PDF page number case"}).json()

    with open(FIXTURE_PATH, "rb") as f:
        content = f.read()
    doc = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("sample_multipage.pdf", content, "application/pdf")},
    ).json()
    assert doc["status"] == "INGESTED"
    assert doc["document_type"] == "PDF"

    result = client.post(f"/api/documents/{doc['id']}/process").json()
    assert result["ok"] is True
    assert len(result["evidence_created"]) == 3  # one marker sentence per page

    page_numbers_seen = set()
    expected_by_page = {
        1: "PAGE ONE MARKER: The delivery van arrived at the warehouse on 3 June.",
        2: "PAGE TWO MARKER: The manager signed the intake log at 09:15.",
        3: "PAGE THREE MARKER: No damage was reported at the time of intake.",
    }
    for eid in result["evidence_created"]:
        ev = client.get(f"/api/evidence/{eid}").json()
        assert ev["page_number"] is not None, "PDF evidence must carry a real page number"
        assert ev["source_location_known"] is True
        page_numbers_seen.add(ev["page_number"])
        # The page number must match the page the text actually came from --
        # never a fabricated or off-by-one value.
        assert ev["source_text"].strip() == expected_by_page[ev["page_number"]]

    assert page_numbers_seen == {1, 2, 3}


def test_txt_evidence_has_no_fabricated_page_number(client):
    """Contrast case: TXT has no pagination, so page_number must stay None
    and source_location_known must stay False -- never defaulted to page 1."""
    case = client.post("/api/cases", json={"title": "TXT no-page case"}).json()
    content = b"A single-page-equivalent plain text document with no real pagination."
    doc = client.post(
        f"/api/cases/{case['id']}/documents",
        files={"file": ("plain.txt", content, "text/plain")},
    ).json()
    result = client.post(f"/api/documents/{doc['id']}/process").json()
    for eid in result["evidence_created"]:
        ev = client.get(f"/api/evidence/{eid}").json()
        assert ev["page_number"] is None
        assert ev["source_location_known"] is False
