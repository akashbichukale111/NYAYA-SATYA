# Case Continuity Engine

**"Never lose the state of a case."**

An agentic case-state continuity system. It turns fragmented legal
documents, orders, hearings, filings, deadlines, and actions into a
continuously maintained **Case Digital Twin**, detects what changed,
determines what remains unresolved, preserves institutional context, and
safely prepares the next required workflow - always with a human in the
loop for anything ambiguous or high-impact.

This is **not** a legal chatbot, a document summarizer, or a case-status
scraper. It is a persistent case-state intelligence and continuity system.

> Built for Code for a Billion / Timely Justice - Legal Backlog.
> Standalone flagship submission; designed to later plug into NYAYA-SATYA
> as `🔄 Case Continuity Engine` (see `docs/NYAYA_SATYA_INTEGRATION.md`).

---

## 1. The problem

Legal case information accumulates across pleadings, orders, hearings,
notices, evidence, replies, and human/agent actions over long periods. The
hard question isn't "does the information exist" - it's:

> **What is the current, true state of this case - and what changed to get
> here, on what evidence, with what still unresolved?**

## 2. The core model

```
RAW EVENT → EXTRACT → VERIFY → CLASSIFY → COMPARE WITH CURRENT STATE
  → DETECT CHANGE → UPDATE CASE DIGITAL TWIN → IDENTIFY CONSEQUENCES
  → CREATE PENDING WORK → HUMAN REVIEW WHEN REQUIRED → VERIFY
  → CREATE NEW VERSION → AUDIT
```

The system **never** silently overwrites history, and an LLM **never**
writes directly to case state - every state transition is a proposal that
passes through verification and (for anything ambiguous or high-impact) a
human review gate before it becomes a new, immutable state version.

## 3. How this differs from a "Hearing Readiness Engine"

| | Question it answers |
|---|---|
| Hearing Readiness Engine | "Is this case ready for the next hearing?" |
| **Case Continuity Engine** | "What is the continuously evolving state of this case, what changed, what's unresolved, and what must happen next?" |

This project deliberately does not rebuild hearing-readiness logic. It owns
case-state evolution; a future Hearing Readiness Engine can *consume* this
engine's trusted current state (see `docs/NYAYA_SATYA_INTEGRATION.md`).

---

## 4. Architecture

```
case-continuity-engine/
├── backend/
│   ├── app/
│   │   ├── models.py            # Full domain model (SQLAlchemy)
│   │   ├── database.py          # Engine/session setup
│   │   ├── config.py            # Env-driven settings
│   │   ├── security.py          # File validation, path safety, prompt-injection defense
│   │   ├── llm_provider.py      # LLMProvider abstraction (Mock + Anthropic)
│   │   ├── state_twin.py        # Case Digital Twin snapshot builder
│   │   ├── diff.py              # State Diff Engine
│   │   ├── freshness.py         # State Freshness model
│   │   ├── graph.py             # Continuity Graph builder
│   │   ├── continuity_health.py # Continuity Health panel
│   │   ├── evaluation.py        # Evaluation Lab (honest MEASURED/NOT_MEASURED metrics)
│   │   ├── simulation.py        # Counterfactual + future-state simulation (clone-only)
│   │   ├── demo_data.py         # Synthetic demo cases A-H
│   │   ├── agents/               # 10 agents + orchestrator (see below)
│   │   └── routers/              # REST API (see section 8)
│   ├── tests/                    # pytest suite
│   └── main entrypoint: app/main.py
├── frontend/                     # Vanilla HTML/CSS/JS command-center UI (no build step)
├── docs/                         # This README + NYAYA-SATYA integration contract
├── scripts/                      # run_tests.sh, seed_demo.sh
└── docker-compose.yml
```

No giant backend file, no giant frontend component, no business logic
hidden in the UI - domain logic lives in `app/*.py` and `app/agents/*.py`;
routers are thin HTTP adapters over it.

## 5. The Case Digital Twin

Represented with **proper relational domain models**, not a JSON blob:
`Case`, `Party`, `Event` (append-only), `Document`, `Evidence`, `Hearing`,
`Order`, `Deadline`, `Obligation`, `Action`, `StateVersion`, `StateChange`,
`Conflict`, `ChangeProposal`, `Verification`, `Handoff`, `Simulation`,
`AgentRun`, `AuditEvent`. See `backend/app/models.py` for the full schema
and relationships.

## 6. Event-sourced history & state versioning

- `Event` rows are **append-only** and never mutated or deleted by normal
  application code.
- Every committed change produces a new immutable `StateVersion` (V0, V1,
  V2, ...), each with a materialized snapshot (a cache, not the source of
  truth - the relational tables are the source of truth).
- The **State Diff Engine** (`app/diff.py`) compares any two versions and
  reports ADDED / REMOVED / CHANGED per entity collection, each linked back
  to its source event.
- Nothing is ever hard-deleted to reflect staleness: the **Staleness
  Agent** marks superseded rows `SUPERSEDED` and links them to the event
  that superseded them (see `app/agents/staleness_agent.py`), so the
  **Time Machine** can always show what the state looked like *then*.

## 7. Agentic architecture

Ten agents, each with real responsibilities (not decoration):

| Agent | File | Responsibility |
|---|---|---|
| Intake | `agents/intake_agent.py` | Validate, hash, store an artifact; record `DOCUMENT_UPLOADED` |
| Event Extraction | `agents/event_extraction_agent.py` | Turn document text into structured candidate facts (via `LLMProvider`) |
| Change Detection | `agents/change_detection_agent.py` | Classify new/duplicate/contradiction/update/correction/stale/ambiguous/unrelated; emit `ChangeProposal`s |
| Contradiction | `agents/contradiction_agent.py` | Detect conflicting pending proposals; create `Conflict` records showing both sources |
| Staleness | `agents/staleness_agent.py` | Mark superseded rows `SUPERSEDED`, never delete |
| Verification | `agents/verification_agent.py` | Run required checks before any commit; can produce `VERIFICATION FAILED` |
| State Reconciliation | `agents/reconciliation_agent.py` | The **only** code path that writes to twin tables; builds the new `StateVersion` + `StateChange` rows |
| Context/Handoff | `agents/context_agent.py` | Build the "what does the next human/agent need to know" structured handoff |
| Timeline | `agents/timeline_agent.py` | Assemble the ordered, filterable event timeline |
| Audit | `agents/audit_agent.py` | Read-side query over the append-only audit trail |

Orchestrated by `agents/orchestrator.py` following:

```
OBSERVE → EXTRACT → COMPARE → INVESTIGATE → PROPOSE CHANGE → VERIFY
  → HUMAN REVIEW IF REQUIRED → COMMIT NEW STATE VERSION
  → UPDATE CONTINUITY GRAPH → AUDIT
```

**An LLM never writes to the database.** High-confidence, unambiguous, new
(non-conflicting) facts may auto-commit after passing verification;
anything else - updates to existing state, low-confidence extractions,
anything flagged for possible prompt injection, or anything involved in a
detected conflict - is held at the **Human Review Gate**
(`POST /api/cases/{id}/proposals/{id}/review` with `approve` / `edit` /
`reject`) before it can ever become a new state version.

## 8. REST API

All routes are under `/api`. See `backend/app/routers/` for the FastAPI
route definitions (and `/docs` for interactive Swagger once running).

```
GET  /api/cases                                  list cases
POST /api/cases                                  create a case
GET  /api/cases/{id}                             case detail
POST /api/cases/{id}/ingest                       upload + process an artifact
GET  /api/cases/{id}/events                       event history
GET  /api/cases/{id}/state                        current state + freshness
GET  /api/cases/{id}/versions                     state version list
GET  /api/cases/{id}/versions/{n}                 one version's snapshot
GET  /api/cases/{id}/diff?from=X&to=Y             state diff engine
GET  /api/cases/{id}/timeline                     ordered timeline
GET  /api/cases/{id}/graph                        continuity graph (nodes/edges)
GET  /api/cases/{id}/changes                      "What Changed?" (latest vs previous version)
GET  /api/cases/{id}/conflicts                    conflicts
POST /api/cases/{id}/conflicts/{cid}/resolve      mark a conflict resolved
GET  /api/cases/{id}/proposals                    change proposals (human review gate)
POST /api/cases/{id}/proposals/{pid}/review       approve / edit / reject
GET  /api/cases/{id}/continuity-health            continuity health panel
POST /api/cases/{id}/handoff                      prepare a handoff context
POST /api/cases/{id}/handoff/{hid}/approve        approve a handoff
POST /api/cases/{id}/simulate/remove              counterfactual: remove an item (clone only)
POST /api/cases/{id}/simulate/field-change        counterfactual: change a field (clone only)
POST /api/cases/{id}/simulate/future-state        workflow projection (not a legal-outcome prediction)
GET  /api/cases/{id}/audit                        audit trail + agent run history
GET  /api/evaluation?case_id=                     evaluation lab metrics
POST /api/demo/seed                               seed the 8 synthetic demo cases
GET  /api/healthz                                 health check
```

## 9. Security

- File uploads are validated by extension (`.pdf .docx .txt .json .csv`),
  size-limited, and filenames are sanitized against path traversal
  (`app/security.py::validate_upload`, `safe_store_path`).
- Every artifact is hashed (SHA-256) on intake.
- Uploaded document text is **untrusted data**. It is wrapped in an
  explicit `<untrusted_document_content>` marker before ever reaching an
  LLM call (`sanitize_for_prompt`), and a heuristic scanner
  (`detect_prompt_injection`) flags documents that look like they're trying
  to hijack agent behavior - flagged documents force **every** derived
  proposal into human review, regardless of confidence (see demo Case F).
- Case data is stored in per-case directories; `safe_store_path` rejects
  any path-traversal attempt in a case id or filename.
- Cross-case isolation is asserted by an automated test
  (`tests/test_case_isolation.py`) and reported as a `MEASURED` metric in
  the Evaluation Lab.
- The `LLMProvider` abstraction means the frontend **never** receives an
  API key - only the backend process reads `LLM_API_KEY` from the
  environment.

## 10. Legal safety

The system does **not**: predict a verdict, determine guilt or innocence,
determine a sentence, advise deceiving a court, fabricate or alter or
conceal evidence, impersonate a lawyer or judge, or make a final legal
decision. Its role is continuity, state management, evidence traceability,
workflow context, and human-reviewed assistance - full stop. The
Simulation engine is explicitly restricted to workflow/procedural
projections and counterfactual "what if this administrative fact were
different" views, and every simulation result is labeled `SIMULATION ONLY`.

## 11. Demo mode (works with zero external dependencies)

`LLM_PROVIDER=mock` (the default) uses a deterministic, offline,
regex/keyword-based extraction provider (`MockLLMProvider` in
`app/llm_provider.py`) - no API key, no network call, fully reproducible.
Switch to a real model by setting `LLM_PROVIDER=anthropic` and
`LLM_API_KEY` in the environment; nothing else in the codebase needs to
change (`app/llm_provider.py::AnthropicLLMProvider`).

### Synthetic demo cases (`POST /api/demo/seed`)

All fictional; no real personal legal information. Each is built by
running real documents through the real pipeline (not hand-faked):

| Case | Demonstrates |
|---|---|
| A | Simple evolving case (filing → deadline) |
| B | Multiple state transitions across several documents |
| C | Conflicting sources (two notices, two different deadlines → `Conflict`) |
| D | Superseded order/deadline (staleness agent marks the old row `SUPERSEDED`, never deletes) |
| E | Stale state (backdated events → freshness model reports `STALE`/`AGING`) |
| F | A document containing prompt-injection-style language → flagged, all derived proposals forced to human review |
| G | An ambiguous event with no strong structural signal |
| H | A deliberately invalid proposal → `VERIFICATION FAILED` |

## 12. Evaluation Lab

`GET /api/evaluation` reports real, computed metrics from this instance's
own data (agent run success rate & latency, verification pass rate,
provenance coverage, state-version integrity, cross-case isolation).
Metrics that would require a labeled ground-truth dataset (extraction
accuracy, change-detection precision/recall, false positive/negative
rates) are explicitly reported as `NOT_MEASURED` with the reason why,
rather than invented - see `backend/app/evaluation.py`.

## 13. Testing

```bash
./scripts/run_tests.sh
```

Covers: API basics, state versioning, the diff engine, change detection,
contradiction detection, staleness/supersession, verification + human
review, security (file validation, path traversal, prompt-injection
flagging), simulation (clone-only, never touches real state), and
cross-case isolation. All 31 tests pass against the codebase as shipped.

## 14. Installation & running

**Requirements:** Python 3.11+.

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
cp ../.env.example .env        # optional - defaults to offline mock mode
python3 -m uvicorn app.main:app --reload
```

Then open **http://localhost:8000** - the backend serves the frontend as
static files, so this one process is the whole product. Click **"Seed demo
cases"** in the top bar to load the 8 synthetic cases, or create a new case
and upload your own `.txt` (or `.pdf`/`.docx`/`.json`/`.csv`) documents.

Or with Docker:

```bash
docker compose up --build
```

### Environment variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./case_continuity.db` | SQLAlchemy connection string |
| `UPLOAD_DIR` | `./uploads` | Per-case document storage root |
| `MAX_UPLOAD_MB` | `15` | Upload size limit |
| `LLM_PROVIDER` | `mock` | `mock` (offline) or `anthropic` |
| `LLM_API_KEY` | *(empty)* | Only read server-side; never sent to the frontend |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model id for the Anthropic provider |
| `LLM_BASE_URL` | `https://api.anthropic.com` | API base URL |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## 15. Frontend

Vanilla HTML/CSS/JS - no build step, no framework, no bundler. Covers every
navigation item from the spec: Command Center, Cases, Current State, What
Changed, Timeline (with artifact upload), Case Graph (typed SVG graph),
Handoff, Conflicts, Simulate, Time Machine (version scrubber + replay +
compare-with-current), Evaluation Lab, Audit, Settings. `frontend/app.js`
talks only to this backend's own API - it never calls an LLM directly and
never sees an API key.

## 16. Limitations (stated plainly, not hidden)

- The Mock LLM provider is a transparent, regex/keyword-based heuristic,
  not real NLP - it's what makes the demo reproducible offline, not a
  claim of extraction sophistication. Point `LLM_PROVIDER` at a real model
  for higher-quality extraction.
- The Continuity Graph is rendered as a simple layered SVG (grouped by
  type, straight edges) rather than a physics-based force layout - chosen
  for reliability and zero external dependencies over visual polish.
- No authentication/authorization layer exists yet - `app/security.py`
  handles file/path safety and case-scoped storage, but there is no login
  system. Role-based access is left as an integration-time concern (see
  `docs/NYAYA_SATYA_INTEGRATION.md`).
- Evaluation metrics that need a labeled dataset are `NOT_MEASURED` by
  design - see section 12.
- No localization strings have been extracted into a translation layer yet
  (English only); the architecture doesn't hard-code English into logic,
  but a translation file/lookup layer is `NOT IMPLEMENTED`.

## 17. Future roadmap

- Real NLP/LLM extraction pipeline improvements (structured function
  calling against `LLM_PROVIDER=anthropic`) and a labeled evaluation set
  to make the `NOT_MEASURED` metrics real.
- Localization layer (Marathi, Hindi, other Indian languages).
- Authentication/authorization + multi-tenant isolation hardening.
- API versioning (`/v1/`) ahead of a real NYAYA-SATYA integration.
- A physics-based Continuity Graph layout.

## 18. NYAYA-SATYA integration

See `docs/NYAYA_SATYA_INTEGRATION.md` for the full input/output contract.
In short: this engine is the trusted source of case state; a consumer
(including a future Hearing Readiness Engine) integrates purely over this
repository's existing REST API, read-only, with no shared database and no
tight coupling in either direction.

---

*This is a hackathon-grade reference implementation. No claims of
real-world deployment, "world first" status, or measured real-world impact
are made anywhere in this repository.*
