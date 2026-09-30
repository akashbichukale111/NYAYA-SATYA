# Registry Defect Engine

> **"Find the filing defect before it becomes the case bottleneck."**

Project 08 in a larger legal-tech system. This module will later integrate
into **NYAYA-SATYA — Adversarial Evidence & Case Reasoning System for
Timely Justice** via a read-only operational summary (see
[docs/nyaya-satya-integration.md](docs/nyaya-satya-integration.md)), but it
is fully independent and runnable on its own.

## What this is — and isn't

The Registry Defect Engine analyzes a filing package (documents, metadata,
procedural records, and explicitly supplied submission requirements) and
surfaces **documented or structurally detectable** defects: missing
documents, broken attachment references, metadata conflicts, duplicate or
ambiguous document versions, and unresolved registry objections.

It is **not**:
- a court registry, a judge, or a legal-validity oracle
- a system that predicts whether a court or registry will accept a filing
- a system that invents filing requirements, deadlines, or fees
- an autonomous filer — it never submits anything or contacts a registry
- a mental-health, medical, or general legal-advice tool

Every defect the engine reports links back to concrete evidence (a document,
a requirement, a detected reference) and states plainly what a human needs
to check. See **Safety boundary** below for the exact rules this codebase
follows.

## Safety boundary

These rules are enforced in code, not just in prose:

- **The engine never invents a requirement.** Every `Requirement` row must
  declare a `source` (`SOURCE_DOCUMENT`, `USER_PROVIDED_CHECKLIST`,
  `AUTHORIZED_TEMPLATE`, `CONFIGURED_REGISTRY_RULE`,
  `IMPORTED_REQUIREMENT_SET`, or `UNKNOWN`). A requirement with an
  unknown/unsupported source is stored with `status=UNKNOWN` and
  `verification_status=UNKNOWN` — it is never silently promoted to
  `ACTIVE`. See `backend/app/services/requirement_engine.py` and
  `tests/test_requirement_engine.py::test_requirement_with_unknown_source_is_never_active`.
- **The engine never fabricates a source location.** Page/section numbers
  in evidence are only ever recorded when the parser actually determined
  one; otherwise the record is `SOURCE_LOCATION_UNKNOWN`. See
  `backend/app/services/parsing.py`.
- **Defect severity means operational attention, not legal consequence.**
  Severities are `INFO` / `ATTENTION` / `HIGH_ATTENTION` /
  `REQUIRES_HUMAN_REVIEW`. Defect description templates never claim a
  filing will be rejected or is legally invalid — see
  `backend/app/services/defect_engine.py`.
- **Metadata conflicts are recorded, never resolved automatically.** When
  two documents disagree, both values are stored side by side with
  `status=UNRESOLVED`; there is no code path that decides which is
  correct. See `backend/app/services/metadata_engine.py`.
- **Duplicates are never deleted.** The duplicate engine only ever creates
  a `DuplicateGroup` for human review.
- **Nothing consequential happens without a human decision.** A `Defect`
  can only leave its system-detected state through an approved/rejected
  `ReviewTask` (`backend/app/routers/review.py`); this is the only code
  path that writes `CONFIRMED`/`REJECTED` onto a defect.
- **Uploaded documents are untrusted data.** Text resembling an attempt to
  instruct an automated system (e.g. "ignore all previous instructions")
  is flagged as a `PROMPT_INJECTION_CONTENT` security defect for human
  review — it is never treated as an instruction. See
  `backend/app/services/security_scan.py`.
- **Every consequential action is audited, append-only.** See
  `backend/app/core/audit.py` — no code path updates or deletes an
  `AuditEvent`.

## Architecture

```
registry-defect-engine/
├── backend/            FastAPI + SQLAlchemy + SQLite (Postgres-ready)
│   ├── app/
│   │   ├── core/       database, ids, RBAC/case-isolation, audit
│   │   ├── models/     SQLAlchemy domain model
│   │   ├── services/   parsing + requirement/checklist/attachment/
│   │   │               metadata/duplicate/defect engines, precheck
│   │   │               orchestrator, demo seeding
│   │   ├── routers/    REST API endpoints
│   │   └── main.py     app entrypoint
│   └── tests/          pytest suite (unit, API, reasoning-flow)
├── frontend/           React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── pages/      Command Center, Cases, Filing Package workspace
│       ├── components/ Layout, shared UI
│       └── lib/        typed API client, session, status mappings
├── docs/               architecture and subsystem documentation
├── demo/               (demo data is seeded via API/script, not files)
└── docker-compose.yml
```

See [docs/architecture.md](docs/architecture.md) and
[docs/domain-model.md](docs/domain-model.md) for more detail.

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
. venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. On startup, tables are created automatically
if missing (SQLite file `backend/registry_defect_engine.db` by default).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` requests
to `http://localhost:8000` (see `frontend/vite.config.ts`).

### Docker

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:8080`. (Compose file provided; not
verified against a live Docker daemon in this build environment — please
report an issue if it doesn't come up cleanly.)

## DEMO mode

The engine ships with **3 deterministic synthetic cases**, seeded via:

```bash
curl -X POST http://localhost:8000/api/demo/seed
```

or by clicking "Load demo cases" on the Command Center. Every demo case has
`is_demo=true` and the frontend renders a
**"DEMONSTRATION DATA — NOT A REAL CASE"** banner on it. The three cases:

- **Demo A — Missing Attachment**: a petition references "Annexure B" in
  its text; Annexure B was never uploaded. The engine detects
  `MISSING_REFERENCED_ITEM`.
- **Demo B — Metadata Conflict**: two documents in the same package declare
  different case numbers. The engine detects `IDENTIFIER_MISMATCH` and
  leaves it `UNRESOLVED`.
- **Demo C — Objection + Correction**: a registry objection is recorded,
  linked to a defect, a correction is planned and simulated-submitted, and
  a `Verification` is left `PENDING` — showing the full
  objection → defect → correction → verification lifecycle.

Demo mode requires **no external API keys** — see `LLMProvider` in
`docs/agent-system.md` for how the deterministic path works with or
without an LLM configured.

## Environment variables

See [.env.example](.env.example). Nothing is required for DEMO mode or core
detection; `DATABASE_URL` and `STORAGE_ROOT` are the only variables most
deployments need to change.

## Testing

```bash
cd backend
. venv/bin/activate
python -m pytest tests/ -v
```

As of this build: **91 tests, all passing** — unit tests for parsing,
requirement engine, attachment reference extraction, metadata conflicts,
duplicate detection, dependency graph / defect impact analysis, the
LLMProvider abstraction, the counterfactual simulator and 12-scenario
crash test, the Time Machine, and the verification and version/supersession
engines; API tests for case CRUD, RBAC, case isolation, document upload
(path-traversal, dangerous-extension, oversized-file rejection), and the
full analysis endpoint set (dependency-graph, simulation, crash-test,
time-machine, evaluation, defect verify/impact); a dedicated security test
file (`tests/test_security.py`) covering path traversal, oversized upload,
prompt-injection-in-upload, double-extension evasion, and cross-case
access; end-to-end reasoning-flow tests covering missing-attachment,
unknown-requirement, review-approve/reject, and objection-lifecycle
scenarios; and a pytest wrapper that actually executes the Evaluation Lab's
13 scenarios and asserts every one passes. See `backend/tests/` — nothing
here is claimed without a test actually being run.

```bash
cd frontend
npm run build   # type-checks and builds; verified clean as of this build
```

## Security

- File uploads: extension allowlist, dangerous-extension rejection, size
  limit (25 MB), SHA-256 hashing, generated (never client-supplied)
  storage filenames to prevent path traversal, and parser failures are
  captured as data rather than raised as crashes.
- RBAC: a deny-by-default capability matrix
  (`backend/app/core/security.py`) restricts requirement creation,
  precheck, review approval/rejection, crash tests, and audit viewing by
  role (`CITIZEN`, `LEGAL_AID`, `ADVOCATE`, `ADMIN`).
- Case isolation: every case-scoped query is filtered by `case_id`, and
  access to a case is denied by default unless the requesting user owns it
  or holds `ADMIN`. Covered by `tests/test_api_cases.py` and
  `tests/test_api_documents.py`.
- Prompt-injection defense: see Safety boundary above.

Full detail in [docs/security.md](docs/security.md) and
[docs/privacy.md](docs/privacy.md).

## Current build status and limitations

This repository is being built in the four execution sections described in
the original build brief. **As of this commit:**

- ✅ Section 1 (core system): domain model, ingestion, requirement/
  checklist/attachment-reference/metadata/duplicate/defect engines,
  precheck orchestrator, core REST API, demo seeding, initial frontend,
  foundational tests — implemented and tested.
- ✅ Section 2 (intelligence + governance): `LLMProvider` abstraction
  (Mock/OpenAI/Anthropic/Groq, DEMO mode uses Mock only, others fall back
  to Mock without a key or on any API error), version/supersession engine,
  verification engine (re-runs the real underlying check, never
  auto-resolves on a mere file change), defect dependency graph, defect
  impact analysis, Time Machine (built entirely from data already never
  deleted — DocumentVersion rows and the append-only audit log, no
  separate snapshot table), counterfactual simulation and the full
  12-scenario registry crash test (both provably non-destructive — they
  operate on an in-memory deep copy and the only DB write is the
  `Simulation` record of what was asked and found), and the Evaluation Lab
  (13 scenarios, all executed for real against fresh isolated cases on
  every call, PASS/FAIL/NOT_RUN only, never a percentage) — implemented
  and tested. RBAC now also gates simulation (`LEGAL_AID`+) and crash
  tests (`ADVOCATE`+).
- ⏳ Section 3 (premium frontend + flagship demo polish) — the frontend
  currently covers all core workspace tabs functionally but has not had a
  dedicated visual-design pass, and the dependency-graph/Time-Machine/
  crash-test/simulation/evaluation screens are backend-complete but have
  no frontend pages yet.
- ⏳ Section 4 (final hardening + delivery audit) — not yet run.

Known limitations right now:
- No password-based authentication; a "session" is an identified role via
  `X-User-Id` (see `backend/app/routers/users.py`). Not production auth.
- DOCX/CSV/JSON parsing does not attempt page-number recovery (DOCX has no
  reliable page concept without a rendering engine) — this is intentional
  per the "never fabricate a page number" rule, not an oversight.
- Docker Compose setup has not been verified against a live Docker daemon
  in this environment.

## Integration with NYAYA-SATYA

See [docs/nyaya-satya-integration.md](docs/nyaya-satya-integration.md). In
short: `GET /api/integration/nyaya-satya/cases/{case_id}/summary` returns a
plain operational summary (counts and id lists, no synthesized legal
judgment). Nothing in this codebase calls out to a NYAYA-SATYA service —
the adapter is one-directional and this module remains fully standalone.
