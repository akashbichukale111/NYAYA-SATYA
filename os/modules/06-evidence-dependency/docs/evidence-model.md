# Evidence model

## Provenance is never fabricated

`EvidenceItem` carries `page_number`, `section`, and `source_location_known`.
The rule enforced throughout the codebase:

- If the source format supports real pagination (PDF, via PyPDF2) and the
  evidence was extracted from a specific page, `page_number` is set to that
  **actual** page index and `source_location_known=True`.
- If the source format has no reliable pagination (TXT, JSON, CSV, DOCX in
  this implementation -- python-docx doesn't expose page boundaries because
  DOCX doesn't have fixed pages until rendered), `page_number` stays `None`
  and `source_location_known=False`.
- Nothing in the codebase ever defaults `page_number` to `1` or invents a
  section name. `source_location_known=False` is a normal, expected,
  frequently-occurring state, not an error.

This is proven by `tests/unit/test_pdf_provenance.py`, which uses a real
generated 3-page PDF fixture (`tests/fixtures/sample_multipage.pdf`) and
asserts each extracted evidence item's `page_number` matches the actual
page its text came from, and contrasts this with a TXT upload where every
extracted item correctly has `page_number=None`.

## Anti-fabrication contract for extracted evidence

`EvidenceExtractionAgent` (`app/agents/evidence_extraction_agent.py`) only
ever creates an `EvidenceItem` whose `source_text` is a verbatim substring
of the actual parsed document text at that location. This is enforced
twice: once inside `MockProvider.extract_evidence_candidates` (asserts the
candidate string is `in text`) and again in the agent itself before
`db.add()`. `tests/unit/test_document_ingestion.py::test_document_process_pipeline_creates_grounded_evidence_and_claims`
verifies this end-to-end against a real uploaded file.

`ClaimDiscoveryAgent` carries the same guarantee one level further: a
discovered claim's `text` is set to its originating evidence item's own
`source_text` -- never a paraphrase, never an inference beyond what the
source literally says.

## Evidence states vs. verification status

These are two different axes and both matter:

- `EvidenceState` describes the evidence's relationship to the world
  (is it supported, contradicted, superseded, excluded...).
- `VerificationStatus` describes whether a human has confirmed it.

An evidence item can be `SUPPORTED` (graph-derived: it has corroborating
evidence) while still `UNVERIFIED` (no human has looked at it yet) --
these are tracked independently and both are surfaced in every API
response so the UI (once built) never has to guess which one to show.

## Evidence Digital Twin (partial)

The spec's "Evidence Digital Twin" concept -- current state, what changed,
why, and historical state, all in one view -- is implemented as data, not
yet as a single combined API endpoint:

- Current state: `GET /api/evidence/{id}`
- What changed / why: `GET /api/evidence/{id}/current-vs-previous` (real
  diff between the two most recent `EvidenceVersion` snapshots, including
  the `reason` string recorded at write time, e.g. `"AGENT_EXTRACTED"` or
  `"REVIEW_APPROVED:CHANGE_VERIFIED_STATUS"`)
- Historical state: `GET /api/evidence/{id}/history` (full version list) and
  `GET /api/evidence/{id}/diff?from_version=X&to_version=Y` (any two
  versions)
- Linked claims/issues/relationships/conflicts: not yet combined into one
  response -- today a caller assembles this from
  `GET /api/cases/{case_id}/relationships` (filtered client-side) plus the
  evidence endpoints above. A single `GET /api/evidence/{id}/digital-twin`
  endpoint that assembles all of this server-side is a reasonable next
  step (see docs/status.md).

## Temporal fields not yet enforced

`EvidenceItem` has `event_date`, `discovery_date`, `valid_from`,
`valid_until`, and `supersession_date` columns, and `Document` has
`superseded_by_document_id`. These are stored and returned but nothing in
the current services automatically excludes an evidence item whose
`valid_until` has passed, or automatically walks a supersession chain.
This is a deliberate scope boundary for this pass, not an oversight: the
spec is explicit that the system should never make automatic legal
determinations, and "this evidence's validity window has expired" edges
close to that line, so it's left as a value a human reviewer sees and
acts on, not something the system enforces silently.
