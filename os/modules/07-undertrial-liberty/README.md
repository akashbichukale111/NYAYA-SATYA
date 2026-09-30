# Undertrial Liberty Sentinel

> "Never let a critical liberty-related event disappear inside a fragmented case record."

Project 07 in the NYAYA-SATYA legal-tech system. This tool **organizes, traces,
monitors, and surfaces** procedural liberty-related events, dates, custody
information, orders, hearings, missing information, and human-review alerts
for undertrial cases.

## What this is NOT

This is **not** a legal advice system, bail-decision system, judicial-prediction
system, or automated liberty determination system. It never:
- determines guilt or innocence
- predicts bail approval/rejection or any court decision
- calculates legal entitlement or invents statutory deadlines
- declares detention unlawful
- takes autonomous legal action (filing, contacting authorities, requesting release)

It surfaces information — with full source provenance and explicit uncertainty
labeling — for a **human legal professional** to review. See
[`docs/architecture.md`](docs/architecture.md) for the full safety boundary.

## Status

This build is genuinely functional and has been tested against a running
instance, not just written. See **[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)**
for the honest, current state: what's fully working, what's partial, and what
is a known limitation. Read that file before assuming feature-completeness —
this is a large spec and not every nav item described in the original design
(e.g. a dedicated React Flow dependency-graph visualization, a Settings/RBAC
admin screen) has a frontend page yet, even though the underlying API for it
is implemented and tested.

## Quick start (no API key required)

### Backend

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
python -m app.db.seed_demo      # creates 3 synthetic demo cases
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs, or
`http://localhost:8000/api/health`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

### Docker Compose

```bash
docker compose up --build
```

## Running tests

```bash
cd backend
python -m pytest tests/ -v
```

All 28 backend tests pass as of the last verified run (see PROJECT_STATUS.md
for the exact command output). This includes explicit regression tests for a
real transaction-safety bug found and fixed during development (see
`tests/test_reasoning_and_crashtest.py`).

## DEMO mode

`DEMO_MODE=true` (the default) requires **no external API key**. All
extraction is done by deterministic, rule-based agents
(`app/agents/extraction.py`) rather than an LLM call, so behavior is
reproducible. Three synthetic cases are seeded by `app/db/seed_demo.py`:

- **Demo A** — a clean, fully-documented custody → remand → bail → order →
  release timeline
- **Demo B** — two source documents disagree on an arrest date; the system
  surfaces a conflict and creates a human review task rather than picking one
- **Demo C** — a hearing is on record but no result/order was ever ingested;
  the attention engine flags the procedural gap

Every demo case is clearly labeled `DEMONSTRATION DATA — NOT A REAL CASE` in
the UI.

## Environment variables

See [`.env.example`](.env.example). Nothing is required to run in DEMO mode.
Setting `LLM_PROVIDER=openai|anthropic|groq` plus the matching API key switches
document text through that provider instead of the rule-based mock (see
`app/core/llm.py`); the structured extraction contract stays the same either way.

## Architecture

See [`docs/architecture.md`](docs/architecture.md), [`docs/domain-model.md`](docs/domain-model.md),
and [`docs/agent-system.md`](docs/agent-system.md).

## Security & privacy

See [`docs/security.md`](docs/security.md) and [`docs/privacy.md`](docs/privacy.md).
Uploaded documents are treated as **untrusted data** — see
`tests/test_security.py::test_prompt_injection_in_document_does_not_alter_behavior`
for a concrete, passing test of this.

## NYAYA-SATYA integration

`GET /api/cases/{case_id}/integration/nyaya-satya` returns the operational
summary contract described in [`docs/nyaya-satya-integration.md`](docs/nyaya-satya-integration.md).
This module is independently runnable and does not require any other
NYAYA-SATYA component to be present.

## Known limitations

See the "Known limitations" section of `docs/PROJECT_STATUS.md`. In short:
extraction is rule-based/regex, not a trained NLP model; several frontend nav
items from the original spec (dependency-graph visualization, Hearings/Orders/
Bail/Release as standalone pages rather than inside the unified timeline,
Settings/RBAC screen) are backed by working, tested APIs but do not yet have
dedicated frontend pages; auth is a demo header-based scheme, not production
JWT/session auth.
