# Case Bottleneck Engine

**"Find what is actually stopping a case from moving forward."**

Part of the **NYAYA-SATYA** family (Code for a Billion — Track 7, Timely
Justice / Legal Backlog). This is Project 03: a standalone, evidence-grounded
system that investigates *why* a legal case is not progressing, traces the
bottleneck to its real dependency chain (not just the first missing item),
identifies a safe next action, and never moves anything without a human
approving it.

> It does not predict verdicts. It does not decide guilt, innocence, or
> sentence. It does not file anything with a real court. It answers one
> question, explainably: **what, specifically, is blocking this case, and
> what is a safe next step?**

---

## 1. Problem

A case can sit "pending" for months with nobody able to say *why*, precisely.
Section 1 of the build spec lists the real candidate causes — a missing
document, an unresolved service dependency, a contradiction between two
filings, an actor who hasn't acted, a deadline nobody is tracking. This
system turns **"case is pending"** into a **case flow diagnosis**: what's
blocked, since when, what it depends on, who can act, what evidence supports
the claim, what's still unknown, and what would change if it were resolved.

## 2. What this is *not*

- Not a generic legal chatbot.
- Not a task manager that just lists things as "pending."
- Not a dashboard with an opaque "AI score."
- Not an AI judge, verdict predictor, or sentencing tool.
- Not a system that files anything with a real court, or acts without a
  human approving it first.

## 3. Architecture in one picture

```
CASE STATE (Dependency + Transition graph)
    → Bottleneck Discovery Agent      (Section 9)
    → Root Cause Investigator Agent   (Section 10)  — walks depends_on to the true leaf, not the first symptom
    → Evidence Verification Agent     (Section 39/41/42) — checks provenance, excludes quarantined/injected content
    → Impact Agent                    (Section 11)  — workflow impact only, never legal-outcome impact
    → Action Planner Agent            (Sections 20-22) — proposes a SAFE next action, never "wins the case"
    → HUMAN APPROVAL GATE             (Section 23)  — nothing executes without this
    → Action execution (simulated)    (Section 24)  — no autonomous court filing, ever
    → Verification Agent              (Section 25)  — never assumes success
    → Reassessment Agent              (Section 36)  — re-runs discovery; newly-exposed downstream bottlenecks surface
```

Every step is audited with a shared `correlation_id` (`/api/cases/{id}/audit`).
Every bottleneck conclusion carries a `CONFIRMED / LIKELY / POSSIBLE / UNKNOWN`
confidence label — never presented as flat fact (Section 38).

## 4. What is REAL vs DEMO vs NOT IMPLEMENTED

Per Section 65 ("no fake functionality"), here is the honest breakdown.

### Real (fully functional, covered by automated tests)
- Domain model, Case Flow Graph, dependency-chain walking with cycle guards
- Bottleneck Discovery Agent — explainable confidence/attention, not a random score
- Root Cause Investigator — recursive chain-walking with a depth limit and a
  loop guard; runs a structured multi-agent "debate" (no forced consensus)
  when sources genuinely contradict each other
- Evidence Verification Agent — checks every cited evidence ref actually
  exists as a stored document, and explicitly excludes quarantined
  (suspected prompt-injection) documents from being treated as fact
- Action Planner + Human Approval Gate + Verification Agent + Reassessment
  Agent — a real approve → execute → verify → reassess loop that can reveal
  a genuinely new downstream bottleneck (this is the flagship demo moment,
  Section 58, and it is exercised end-to-end in `tests/test_api.py`)
- Simulation ("what if we remove this bottleneck?"), Collapse Test, and
  Crash Test (10 adversarial mutation types) — all provably read-only
  against the real database (see `test_simulate_endpoint_never_mutates_state`
  and `test_crash_test_never_mutates_real_database`)
- Prompt-injection defense — uploaded document content is scanned; anything
  matching a known injection pattern is quarantined and excluded from
  anything the agents treat as fact, while still being shown to a human
  reviewer verbatim (Case H exercises this exact attack)
- Case isolation — an action or bottleneck belonging to Case A returns 404
  through Case B's URL, even with a valid, guessed ID
- Full audit trail with correlation IDs
- 10 synthetic demo cases (A–J, Section 57), each isolating one specific
  bottleneck behaviour (single obvious bottleneck, competing bottlenecks,
  hidden/deep root cause, contradictory sources, recurring dependency
  failure, resolved-then-reopened, verification failure, prompt injection,
  genuinely unknown/insufficient evidence, multi-dependency)
- A working React + TypeScript frontend (Command Center, Case list, the
  "Why is this case stuck?" hero screen with the root-cause chain rendered
  as an inspectable step-by-step forensic view, a dependency/flow-graph SVG
  view, the Action Center with the human approval gate, Simulate, Crash
  Test, Documents — including visibly flagging quarantined content —
  History, and Audit)

### Deliberately simplified (documented, not hidden)
- **18 spec'd entities → fewer tables.** See the docstring at the top of
  `backend/app/models.py` for the exact mapping (e.g. `CaseState + Event`
  collapsed into `CaseEvent`; `Simulation` is never persisted — it is always
  computed on demand and clearly labelled `SIMULATION_ONLY`).
- **No graph database.** The Case Flow Graph is a plain in-memory
  dict-of-nodes structure (`backend/app/graph.py`) rather than a dedicated
  graph engine — correct at the scale this system handles (tens of nodes
  per case, not millions).
- **No React Flow / force-directed layout.** The flow-graph view is a
  small, deterministic, hand-rolled SVG layout (transitions on the left,
  dependencies on the right). This was a conscious choice for visual
  stability and zero extra dependencies, not an oversight — documented in
  `frontend/src/components/FlowGraphView.tsx`.
- **"Action execution" is simulated,** never touching a real court system or
  filing anything (Section 24 explicitly prohibits autonomous filing). Every
  execution result is tagged `"demo": true` in the API response.

### NOT implemented (roadmap, marked as such in the UI's sidebar)
- **AI Provider Abstraction (Section 56).** There is currently **no LLM in
  this build.** All reasoning is deterministic, rule-based, and fully
  explainable over *structured* case data (dependency status, evidence
  presence, timestamps). This was a deliberate scope decision for a
  legal-safety-critical system: rule-based logic has zero hallucination risk
  and every conclusion is traceable to a specific rule. The real gap this
  leaves is **unstructured input**: turning a raw scanned/free-text document
  into the structured `Dependency`/`Event` rows this engine reasons over
  would need an LLM or NLP extraction pipeline in a real deployment — that
  extraction step is out of scope here and assumed to already exist (e.g.
  fed by NYAYA-SATYA's Case Digital Twin, see Section 8 below).
- Time Machine UI, Case Handoff UI, Evaluation Lab UI (shown, disabled, in
  the sidebar as an explicit roadmap marker rather than silently omitted)
- Multilingual UI (Section 53) — English only; no hard-coded-string audit
  has been done to make this a trivial follow-up
- Formal accessibility pass (Section 54) beyond semantic HTML, focus-visible
  defaults, and `prefers-reduced-motion` support already in `index.css`
- Explicit "low-bandwidth mode" toggle (Section 55) — the CSS is responsive
  and collapses gracefully under 820px, but there's no separate
  data-saving/lazy-load mode
- Docker/`docker-compose.yml`
- Postgres — SQLite only, though the ORM is SQLModel/SQLAlchemy, so the
  swap is a connection-string change, not a rewrite

**Never fabricated:** confidence labels, evidence citations, benchmark
numbers, or "AI scores." Where the spec asked for something not built, the
UI says so (see the sidebar's "Roadmap (not built)" section) rather than
faking it.

## 5. Bugs found and fixed during QA (for transparency)

Two real, reproducible bugs were found while exercising this system end to
end, and are now covered by regression tests:

1. **Simulation engine crash** (`sqlalchemy.orm.exc.ObjectDereferencedError`).
   `simulate`/`collapse-test`/`crash-test` cloned live SQLAlchemy-tracked ORM
   rows via `.model_copy(deep=True)`; this corrupts SQLAlchemy's
   instrumentation once the original row leaves scope. Fixed by introducing
   detached `SimDependency`/`SimTransition` dataclasses
   (`backend/app/graph.py`) with zero ORM coupling — this also makes "the
   simulation engine never touches the database" a structural guarantee,
   not just a convention. Regression test:
   `tests/test_graph.py::test_to_sim_clone_is_fully_detached_from_orm`.
2. **Missing cycle guard.** `CaseGraph.unsatisfied_leaf_dependencies()` had
   no protection against a dependency cycle (unlike its sibling method,
   `_depends_transitively`), and would raise `RecursionError` on cyclic case
   data — a real risk given case data can come from messy, hand-entered
   sources. Fixed with a `_seen` frozenset guard. Regression test:
   `tests/test_graph.py::test_depends_transitively_has_cycle_guard`.

## 6. Running it

### Backend
```bash
cd backend
pip install -r requirements.txt
python seed.py            # loads the 10 demo cases (Section 57)
uvicorn app.main:app --reload --port 8000
```
API docs: `http://localhost:8000/docs`. Health check: `/api/health`.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_BASE defaults to http://localhost:8000
npm run dev                # http://localhost:5173
```

### Tests
```bash
cd backend
python -m pytest tests/ -v
```
40 tests, all passing at time of writing — covering the graph engine
(including the two bug-regression tests above), the security/prompt-injection
scanner, all 10 demo-case agent behaviours, the simulation/crash-test
read-only guarantee, and the full flagship API flow end to end (investigate
→ root cause → action → human approval → execute → verify → reassess →
audit trail).

## 7. API surface

```
GET  /api/health
GET  /api/cases
GET  /api/cases/{id}
GET  /api/cases/{id}/flow            GET  /api/cases/{id}/dependencies   (alias)
GET  /api/cases/{id}/flow-health
GET  /api/cases/{id}/events
GET  /api/cases/{id}/documents
GET  /api/cases/{id}/history
GET  /api/cases/{id}/audit
POST /api/cases/{id}/investigate
GET  /api/cases/{id}/bottlenecks
GET  /api/cases/{id}/bottlenecks/{bottleneck_id}
GET  /api/cases/{id}/root-cause?bottleneck_id=...
GET  /api/cases/{id}/impact?bottleneck_id=...
GET  /api/cases/{id}/actions
POST /api/cases/{id}/actions/{action_id}/approve
POST /api/cases/{id}/actions/{action_id}/reject      { "reason": "..." }
POST /api/cases/{id}/simulate                         { "dependency_id": "..." }
POST /api/cases/{id}/collapse-test                    { "dependency_id": "..." }
GET  /api/cases/{id}/crash-test/mutations
POST /api/cases/{id}/crash-test    { "mutation": "...", "target_dependency_id": "..." }
```

## 8. NYAYA-SATYA integration

See [`docs/NYAYA_SATYA_INTEGRATION.md`](docs/NYAYA_SATYA_INTEGRATION.md) for
the exact input/output contract this engine expects from and returns to the
Case Continuity Engine and Hearing Readiness Engine.

## 9. Security (Section 41)

- Filenames are sanitised (path-traversal stripped, extension allow-listed)
  before any content is trusted — `app/security.py`.
- Uploaded document content is hashed (SHA-256) for tamper-evidence.
- A heuristic prompt-injection scanner quarantines suspicious content;
  quarantined text is **never** read by an agent as case fact — it is only
  ever shown back to a human, verbatim, clearly labelled `QUARANTINED`.
  This is exercised end-to-end by demo Case H and its tests.
- Case isolation: every action/bottleneck lookup checks `case_id` matches
  the URL's case, not just that the object exists — tested explicitly
  (`test_action_case_isolation_cannot_approve_across_cases`).
- No secrets are required or committed (there is no LLM key in this build —
  see Section 4 above).

## 10. Legal safety (Section 42)

This system does not, and will not: predict a verdict, determine guilt or
innocence, recommend a sentence, advise deception, fabricate or hide
evidence, make a final judicial decision, or blame a named individual for
delay without evidence (bottlenecks reference *roles*, e.g. "Advocate,"
never named people, unless the case data itself names a role).

## 11. Repository layout

```
case-bottleneck-engine/
├── backend/
│   ├── app/
│   │   ├── models.py            domain model (see docstring for the 18→fewer-tables mapping)
│   │   ├── graph.py             Case Flow Graph + simulation-safe clone types
│   │   ├── security.py          filename/extension safety, hashing, injection scanner
│   │   ├── audit.py             correlation-id audit log writer
│   │   ├── orchestrator.py      the OBSERVE→...→UPDATE agent loop (Section 36)
│   │   ├── simulation.py        simulate / collapse-test / crash-test (read-only, Sections 26-29)
│   │   ├── demo_data.py         the 10 synthetic demo cases A-J (Section 57)
│   │   ├── agents/              one bounded-responsibility agent per file (Section 35)
│   │   └── routers/             cases, bottlenecks, actions, simulation
│   ├── tests/                   40 tests — graph, security, agents, simulation, full API flow
│   ├── seed.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/client.ts        typed fetch wrapper
│       ├── types/domain.ts      TypeScript mirror of backend response shapes
│       ├── components/          RootCauseChain, FlowGraphView, Badges
│       └── pages/                CommandCenter, CaseList, CaseDetail (all tabs)
├── docs/
│   └── NYAYA_SATYA_INTEGRATION.md
└── .gitignore
```

## 12. Engineering philosophy (Section 73, and we mean it)

Depth over feature count. Evidence over assumptions. Root cause over
symptom. Verification over automation. Human control over autonomous legal
decisions. Workflow progress over outcome prediction. Traceability over
black-box output. Measured results over invented metrics.

No claim in this README should be taken as "measured impact" unless it's a
test result you can reproduce with `pytest -v` — none of the numbers above
are aspirational; they're the output of the test run at the time of writing.
