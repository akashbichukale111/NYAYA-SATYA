# Legal-Aid Handoff Engine

**"Carry the case context, not just the case file."**

An agentic legal-aid continuity and handoff system. It turns fragmented
citizen-provided information — a story, documents, dates, deadlines,
questions — into a structured, source-linked case context; identifies
what's missing or contradictory; builds a role-appropriate handoff packet
for the next human reviewer (paralegal, legal-aid worker, advocate); and
verifies that the important context actually survived the handoff.

This is **not** a legal-advice chatbot, a lawyer replacement, or an
outcome predictor. It structures information, flags gaps and conflicts,
scopes information by role and sensitivity, and puts every consequential
step in front of a human before it happens.

## Problem

A citizen's case moves through several people — legal-aid intake,
paralegal, advocate — and at each handoff, information gets lost,
duplicated, or detached from its source. This project targets that one
failure mode: **context loss across handoffs**, not case state (that's a
sibling "Case Continuity" project), not flow bottlenecks, and not hearing
readiness. See `docs/NYAYA_SATYA_INTEGRATION.md` for how these are meant
to compose.

## What's real in this build

Everything below is wired end-to-end and covered by an automated test —
run `pytest` in `backend/` and see for yourself. `docs/LIMITATIONS.md` is
the honest ledger of what's scoped out (OCR for images, most conflict
types beyond dates, a full React frontend, auth, and more) — nothing is
silently faked in the parts that do run.

- **Fact Status Engine** — every fact carries one of `VERIFIED` /
  `DOCUMENT_SUPPORTED` / `USER_REPORTED` / `INFERRED` / `CONFLICTING` /
  `UNKNOWN` / `NOT_PROVIDED` / `SUPERSEDED`. Nothing is silently upgraded
  to "verified."
- **Conflict Engine** — detects same-event, different-date contradictions
  across sources and surfaces them for human review; never auto-resolves.
- **Missing Information Engine** — for each gap: why it's needed, who may
  know it, how to get it, urgency.
- **Handoff Packet Generator + Quality Gate** — builds a role-scoped
  packet from structured case state only (no generative fact invention),
  with an explicit ✓/⚠ checklist instead of a black-box score.
- **Handoff Context Risks** — unsupported facts, unresolved contradictions,
  missing deadlines/documents — flagged, never called "legal risk."
- **Privacy Engine** — a role→sensitivity ceiling
  (`PUBLIC`/`INTERNAL`/`SENSITIVE`/`HIGHLY_SENSITIVE` ×
  citizen/paralegal/legal-aid-worker/advocate/reviewer/admin) that
  actually excludes over-ceiling fields from a packet, with a plain-English
  reason for every decision (Privacy Simulator UI tab).
- **Context Loss Engine** — compares full source case context to what a
  given handoff version actually transmits: preserved / lost / unsupported,
  never a vague fidelity score.
- **Handoff Versioning + diff ("Time Machine")** — every clarification
  response creates an immutable new version; you can diff any two
  versions of the same handoff.
- **Three agents** (Context Packaging, Handoff Review, Context Loss) built
  on a real `LLMProvider` abstraction — runs fully offline against a
  deterministic mock provider by default, or against the real Anthropic
  API if `LLM_API_KEY` is set. Agents narrate deterministic engine output;
  they never invent facts.
- **Handoff Simulator** — non-persistent "what would the receiver see if
  we removed X" preview.
- **Crash Test** — 5 adversarial mutations run against the engine, each
  asserting the system catches it.
- **Prompt-injection guard** — uploaded document text is scanned for
  injection patterns before it's labeled and surfaced.
- **Append-only audit log + agent-run log** — every state-changing
  endpoint writes one audit event (see `docs/UNWIND_INTEGRATION.md`).
- **6 synthetic demo cases** (clean handoff, missing documents, conflicting
  dates, sensitive-field restriction / context loss, clarification loop,
  adversarial document) seeded via one API call.

## Architecture

```
backend/            FastAPI + SQLAlchemy (SQLite by default; swap DATABASE_URL for Postgres)
  models.py          domain model (Case, Fact, Document, Handoff, HandoffVersion, ...)
  facts/              Fact Status / Conflict / Missing-Information engines
  timeline/           Timeline builder
  handoff/            Packet generator, quality gate, risk detection, simulator, crash test
  verification/       Context loss + version diff + handoff verification
  privacy/            Role/sensitivity access-decision engine
  agents/             LLMProvider abstraction + the 3 agents
  ingestion/          Document upload, hashing, safe filenames, OCR abstraction
  security/           Prompt-injection guard
  audit.py            Append-only audit logging
  demo_data.py         Synthetic demo case seeding
  main.py             All API routes
  tests/              pytest — engine unit tests + full API lifecycle tests

frontend/index.html  Single-page vanilla JS client (no build step) — see "Frontend" below

docs/                DOMAIN_MODEL, LIMITATIONS, NYAYA_SATYA_INTEGRATION, UNWIND_INTEGRATION
```

### Frontend note

The master spec called for React + TypeScript + Vite + Tailwind + Framer
Motion + React Flow. This build ships a single-page vanilla JS/HTML client
instead (`frontend/index.html`) — a deliberate trade to keep every screen
wired to real, live data with zero build tooling required to run the demo.
The API is completely framework-agnostic (plain REST + JSON), so porting
tab-by-tab to React touches no backend code. This is recorded, not hidden
— see `docs/LIMITATIONS.md`.

## Running it

```bash
cp .env.example .env      # optional — works with no changes
./scripts/run.sh
```

This installs backend dependencies, starts the API on
`http://127.0.0.1:8000` (interactive docs at `/docs`), and serves the
frontend at `http://127.0.0.1:5173`. Open the frontend, click **Seed demo
cases**, and walk through Command Center → Case Context → Handoff →
Context Loss → Privacy → Simulate → Crash Test → Audit.

No API key is required — the LLM-backed agents run against a
deterministic mock provider unless `LLM_API_KEY` is set in `.env`.

### Manually

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` directly, or serve it with any static
file server (`python3 -m http.server 5173` from `frontend/`).

## Testing

```bash
cd backend
pytest -v
```

14 tests: engine-level unit tests (conflict detection, privacy filtering,
quality-gate blocking) and full API lifecycle tests (case → intake →
handoff → approve → transfer → acknowledge, with audit-trail assertions
at each step). All pass with no network access required.

## API

~38 REST endpoints under `/api/cases/...` — full interactive docs at
`http://127.0.0.1:8000/docs` once running. Key ones:

| Purpose | Endpoint |
|---|---|
| Guided intake | `POST /api/cases/{id}/intake` |
| Upload a document | `POST /api/cases/{id}/documents` |
| Missing information | `GET /api/cases/{id}/missing-information` |
| Generate a handoff packet | `POST /api/cases/{id}/handoffs` |
| Approve / transfer / acknowledge | `POST .../handoffs/{hid}/{approve,transfer,acknowledge}` |
| Request / respond to clarification | `POST .../handoffs/{hid}/clarify[/…​/respond]` |
| Diff two versions | `GET .../handoffs/{hid}/diff?from_version=&to_version=` |
| Context loss report | `GET .../handoffs/{hid}/context-loss` |
| "Why is this visible?" | `GET /api/cases/{id}/privacy-explain?role=` |
| Non-persistent what-if | `POST /api/cases/{id}/simulate` |
| Crash test | `POST /api/cases/{id}/crash-test` |
| Audit trail | `GET /api/cases/{id}/audit` |

## Environment

See `.env.example`. `DATABASE_URL` defaults to a local SQLite file;
`LLM_API_KEY`/`LLM_MODEL`/`LLM_BASE_URL` are optional and only needed to
route the three agents through a real model instead of the offline mock.

## Legal safety

The system never determines guilt/innocence, predicts outcomes, or
fabricates facts or documents. It structures information, flags gaps and
conflicts, prepares questions, and requires human approval before any
consequential handoff (`Handoff.state` cannot reach `TRANSFERRED` without
an explicit `APPROVE` decision — enforced server-side, see
`test_transfer_requires_approval_first`).

## Limitations & Roadmap

Full, itemized list in `docs/LIMITATIONS.md`. Headline items: OCR only
covers plain-text uploads; only date-based conflicts are auto-detected;
no authentication (roles are passed by the caller, not derived from a
session); 6 of the 10 spec'd demo cases are seeded; the Evaluation Lab
metrics (extraction accuracy, latency percentiles, etc.) are not measured
in this build rather than invented.

## Integration contracts

- `docs/NYAYA_SATYA_INTEGRATION.md` — how this project's output feeds a
  Case Continuity system, and where this project's responsibility ends.
- `docs/UNWIND_INTEGRATION.md` — the audit-event shape and what "unwind
  ready" means here.
