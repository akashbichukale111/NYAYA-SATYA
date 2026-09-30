# SPARK Deadline Guardian

> "Know the date. Know the source. Know what depends on it. Know what
> changed. Know what requires human attention."

## What this is

A workflow-intelligence system for tracking consequential dates
(court orders, notices, filings, contracts, obligations) with full
provenance, explicit uncertainty, and a mandatory human-review
checkpoint before anything is treated as verified.

## Status: Section 1 of 4 — Core Foundation (DONE, tested)

This section delivers a real, runnable service. It does **not** yet
include the dependency graph, conflict/supersession detection, the
attention engine, the safe action planner, or the UI — those are
Sections 2–3, built on top of this foundation, not faked here.

### What's actually implemented and passing tests right now

- **FastAPI service** (`app/main.py`) with SQLite persistence (swap
  `SPARK_DB_URL` for Postgres later — no model changes needed).
- **Deterministic date-candidate extractor**
  (`app/services/date_extraction.py`):
  - Explicit dates ("12 March 2026", "2026-04-01", "12/03/2026") are
    parsed to real `datetime` objects.
  - Relative dates ("within 30 days of service") are detected and
    their anchor phrase is captured, but **never** silently resolved
    to a concrete date — that requires an anchor event, which is
    Section 2's dependency engine.
  - Explicit/relative matches don't double-count overlapping spans.
- **Ingestion pipeline** (`app/services/ingestion.py`): text in →
  `Source` row → date candidates → a `Deadline` "digital twin" per
  candidate, all starting in `PENDING_REVIEW`. Nothing is ever
  auto-marked `VERIFIED`. Deduplicates identical source text via
  SHA-256 checksum. Every step writes to an append-only `AuditLogEntry`.
- **Controlled vocabularies** (`app/models/enums.py`) matching the
  spec's provenance/status states exactly — `SOURCE_EXPLICIT`,
  `SOURCE_RELATIVE`, `USER_ENTERED`, `SYSTEM_DERIVED`, `UNVERIFIED`,
  `CONFLICTING`, `SUPERSEDED`, `UNKNOWN`, `REQUIRES_HUMAN_REVIEW`.
- **API**:
  - `POST /api/v1/ingest/text` — ingest a document/note
  - `GET  /api/v1/sources/{id}` — see a source and its candidates
  - `GET  /api/v1/deadlines` — list, filterable by status/provenance
  - `GET  /api/v1/deadlines/{id}`
  - `POST /api/v1/deadlines/{id}/review` — the **only** way a
    deadline becomes `VERIFIED`; requires a named human reviewer
  - `GET  /api/v1/health`
- **11 automated tests, all passing** (`tests/`): extraction logic
  (explicit/relative/mixed/no-match cases) and full API flow
  (ingest → list → human review → verified; dedup; validation).

### Explicitly NOT in Section 1 (so nothing here is oversold)

- Dependency graph / relative-date anchor resolution
- Conflict detection, supersession detection
- Attention engine, safe action planner, approval workflow beyond the
  single review endpoint
- PDF/document parsing (text ingestion only)
- UI / flagship demo
- Integration with SPARK PERSONAL OS or NYAYA-SATYA
- Authentication/authorization (every review call trusts the
  `reviewer` string it's given — fine for local dev, not for
  production; Section 4 hardening will address this)

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs at http://127.0.0.1:8000/docs
```

## Running the tests

```bash
pytest tests/ -v
```

## Project layout

```
app/
  main.py                  FastAPI app assembly
  database.py               engine/session setup
  models/
    enums.py                 controlled vocabularies
    db.py                     SQLAlchemy tables: Source, DateCandidate,
                               Deadline, DependencyEdge, Conflict, AuditLogEntry
  schemas.py                Pydantic request/response models
  services/
    date_extraction.py       deterministic date candidate detector
    ingestion.py              text -> source -> candidates -> deadlines
  api/
    routes.py                 HTTP endpoints
tests/
  test_date_extraction.py
  test_api.py
```

## What Section 2 will build on top of this

The `DependencyEdge` and `Conflict` tables already exist in the schema
(unused so far, on purpose) so Section 2 — dependency graph resolution,
conflict/supersession detection, and the attention engine — plugs
straight into this foundation instead of requiring a schema migration.
