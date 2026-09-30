# SPARK Workflow Autopilot

> "Turn the next safe action into an executable workflow."

The execution/orchestration engine of the Spark ecosystem. Other Spark
engines detect problems (missing evidence, approaching deadlines, registry
defects, hearing-readiness blockers, handoff needs). Workflow Autopilot turns
those signals into structured, reviewable, executable workflows — while
keeping a human in control of every consequential action.

**Status: Sections 1 and 2 of 4 are built and tested. Section 3 (frontend)
and Section 4 (final hardening + full doc set) are not yet done.** This
README describes only what actually exists and runs today.

## What actually works right now

- A real, persistent workflow/task engine (SQLite via SQLAlchemy) — state
  survives process restarts (verified in `crash_test.scenario_workflow_interrupted`)
- 5 workflow templates: evidence gap, deadline preparation, registry defect,
  hearing readiness, legal-aid handoff — each a declarative task graph with
  no hard-coded legal rules
- A dependency graph engine: tasks become `READY` only when their real
  dependencies are `COMPLETED`/`VERIFIED`
- A human approval gate the engine cannot bypass or satisfy itself
  (`system` can never approve or revalidate its own request)
- Verification requirements that block a workflow from reaching `COMPLETED`
  until every verification-required task is actually `VERIFIED`
- Idempotent trigger handling — duplicate `trigger_event_id`s never create a
  duplicate workflow
- Stale-state protection — a workflow whose case has changed since it was
  planned refuses to execute consequential tasks until a human revalidates it
- Conflict detection — competing signals from different engines are
  preserved as an open `ConflictRecord`, never silently resolved by the engine
- A recovery engine — real, derived recovery options for a failed task
  (retry / human review / replace input / cancel), never a fabricated guess
- A simulation lab — "what if this task fails?" runs the real engine code
  against an isolated database transaction that is always rolled back; this
  is unit-tested to genuinely never touch live state
- A 12-scenario crash-test suite that honestly reports `NOT_EVALUATED` for
  the 4 scenarios this codebase doesn't yet defend against, and flags one
  confirmed real gap (see [Known limitations](#known-limitations))
- 12 single-responsibility agents (Trigger, Planning, Decomposition,
  Dependency, Risk, Approval, Execution, Verification, Recovery, Attention,
  Simulation, Audit, Conflict) — thin, real, independently tested wrappers
- 10 integration adapters normalizing named upstream-engine event shapes
  into a common trigger format
- RBAC (5 roles) and case isolation enforced on every API call
- A full audit ledger — every state transition is recorded
- 63 automated tests, all passing, covering every safety-critical property
  above (not just the happy path)

## What is NOT built yet

- **Section 3 — Premium frontend + flagship demo UI.** There is no web UI.
  The 4 flagship demo scenarios exist as a real, working seed script
  (`demo/seed_demo.py`) that drives the actual engine, but there's no
  Command Center / task graph / approval center screens yet.
- **Section 4 — Final hardening + full documentation set.** Only this
  README, `ARCHITECTURE.md`, `AGENTS.md`, `WORKFLOW_MODEL.md`, and
  `INTEGRATION.md` exist so far. `SECURITY.md`, `PRIVACY.md`,
  `EVALUATION.md`, `API.md`, `DEMO.md` are not yet written.
- Retry rate limiting, task timeout tracking, and general object-level
  locking across concurrently-modified operational objects.

## Setup

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn app.api.main:app --reload
```

The API starts at `http://127.0.0.1:8000`. `init_db()` runs automatically on
startup and creates `spark_workflow_autopilot.db` (SQLite) if it doesn't
already exist. No external API keys are required or used anywhere in this
codebase.

## Demo / mock mode

```bash
python3 demo/seed_demo.py
```

Seeds 4 clearly-labeled ("DEMONSTRATION DATA — NOT A REAL CASE") synthetic
cases, each driven through a real scenario against the actual engine:

- **Demo A** — simple happy-path workflow to `COMPLETED`
- **Demo B** — a workflow that stops at a human approval gate, then proceeds
  only after explicit approval
- **Demo C** — a task fails partway through; downstream tasks are blocked;
  recovery is left as a human decision
- **Demo D** — two different upstream engines produce signals for the same
  case; each becomes its own independently-tracked workflow

## Running the tests

```bash
cd backend
export PYTHONPATH=.
python3 -m pytest tests/ -v
```

63 tests, organized by what they actually verify (not just "does it run"):
`test_workflow_planning.py`, `test_idempotency.py`, `test_approval_boundary.py`,
`test_failure_and_verification.py`, `test_rbac_and_isolation.py`, `test_api.py`,
`test_stale_state.py`, `test_conflict.py`, `test_recovery.py`,
`test_simulation.py`, `test_agents.py`, `test_api_section2.py`,
`test_crash_scenarios.py`.

## API surface (Section 1 + 2)

See `ARCHITECTURE.md` for the full list. The one other engines/consumers
should know about:

```
GET /api/cases/{case_id}/workflow-summary
```

returns a stable JSON summary (active/blocked/approval-required workflows,
tasks due, verification pending, attention items) intended for SPARK
Personal OS to consume. See `INTEGRATION.md`.

## Known limitations

The crash-test suite (`GET /api/crash-test/run`) found and honestly reports
one real gap: **deleting a `Dependency` row out from under a task makes that
task's remaining dependency set trivially satisfied**, because the engine
checks "are all *recorded* dependencies satisfied?" rather than "has the
dependency count itself changed unexpectedly?" This is flagged as
`CONFIRMED` risk in the crash-test report, not hidden. Planned fix for
Section 4: soft-delete dependencies and require human review when a task's
dependency count decreases.

Three other scenarios (task duplication outside the planner, service
unavailability, task timeouts, and general cross-workflow object locking)
are reported as `NOT_EVALUATED` because there is no code path yet to
exercise them — not because they were tested and passed.

## Spark ecosystem integration

This is the operational execution layer between the case-analysis engines
and SPARK Personal OS, per the NYAYA-SATYA architecture. See
`INTEGRATION.md` for the adapter contract and `ARCHITECTURE.md` for how it
fits the larger pipeline. Nothing in this codebase makes a legal decision,
files anything, or asserts a case is legally ready — see the "Core
Principle" section of `ARCHITECTURE.md`.
