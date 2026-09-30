# Architecture

## Core principle

The engine detects, plans, decomposes, checks dependencies, classifies risk,
asks a human when required, executes only what is permitted, verifies,
updates state, and audits. It never makes a legal decision, files anything,
or declares a case legally ready. See `app/engine/templates.py` — every
template task list was written by a human and contains zero embedded legal
rules; the engine only sequences generic operational actions (request,
receive, validate, review, execute, verify).

## Layers

```
Upstream engines (evidence, deadlines, registry, hearing readiness, ...)
        |
        v  (raw event dict)
app/adapters/adapters.py  -- normalizes into NormalizedTrigger
        |
        v
app/engine/agents.py::TriggerAgent -- maps trigger_type -> template name
        |
        v
app/engine/planner.py::plan_workflow -- idempotent workflow+task-graph creation
        |
        v
app/engine/execution.py -- state machine: start/complete/verify/fail/cancel
        |                  enforces approval gates + stale-state checks
        v
app/engine/conflict.py -- detects competing signals, preserves both
        |
        v
app/models/models.py (SQLAlchemy/SQLite) -- persistent state, survives restart
        |
        v
app/api/main.py (FastAPI) -- RBAC + case isolation on every route
        |
        v
GET /api/cases/{id}/workflow-summary -- consumed by SPARK Personal OS
```

## Domain model

`Case` -> `Workflow` -> `Task` (`Dependency` edges between tasks) ->
`ApprovalRequest` (0 or 1 open per approval-required task) -> `AuditEvent`
(one row per state transition, ever). `ProcessedEvent` is the idempotency
ledger keyed on the external `trigger_event_id`. `ConflictRecord` preserves
two competing workflow signals until a human resolves them.

Every row that matters for provenance carries a `provenance_id`. Every
workflow records `case_state_version_at_creation` — the case's
`state_version` at the moment it was planned — which is how stale-state
detection works: if `case.state_version` has since moved, a
CONSEQUENTIAL/APPROVAL_REQUIRED task refuses to complete until a human calls
`revalidate_workflow()`.

## State machines

Workflow states and task states are the full enums specified in the product
spec (`app/core/enums.py`) — `DRAFT` through `SUPERSEDED` for workflows,
`TODO` through `CANCELLED` for tasks. `recompute_workflow_status()` derives
the workflow's status from the aggregate of its tasks' statuses after every
transition — it is never set directly by a human or API caller. Completion
requires actual verification: a workflow is not marked `COMPLETED` while any
verification-required task is short of `VERIFIED` (see
`test_failure_and_verification.py::test_workflow_not_completed_until_verification_passes`).

## Approval gate

A task flagged `approval_required` cannot reach `COMPLETED` without an
`ApprovalRequest` in state `APPROVED`. The engine creates the request but
`decide_approval()` explicitly refuses `decided_by="system"` — a real human
actor id is required. A rejected approval blocks the task (and cascades to
block everything downstream) rather than silently completing it.

## Simulation lab isolation

`app/engine/simulation.py` runs the *real* `execution.py` functions
(`fail_task`, `complete_task`, `decide_approval`) against a dedicated
connection with its own outer transaction, using SQLAlchemy's
`join_transaction_mode="create_savepoint"` so the engine code's internal
`session.commit()` calls only release/recreate SAVEPOINTs rather than
touching the outer transaction. The outer transaction is always rolled back.
Note: pysqlite's DBAPI driver only auto-begins a transaction before
INSERT/UPDATE/DELETE, not before SAVEPOINT, which silently breaks this
pattern unless disabled — see the `connect`/`begin` event listeners at the
top of `simulation.py`. This is unit-tested directly
(`test_simulation.py::test_simulate_task_failure_does_not_mutate_live_state`)
rather than assumed.

## RBAC and case isolation

`app/engine/rbac.py` defines 5 roles with additive permission sets.
`require_case_access()` is called on every API route with a `case_id` in the
path — it checks the caller's `X-Case-Access` header set (or a case ID
derived from a task/workflow's own `case_id`), never trusting a
caller-supplied case_id as authorization by itself. `X-Role`/`X-User-Id`/
`X-Case-Access` are demo/mock headers; a real deployment replaces
`app/api/deps.py` with real OAuth/JWT validation without changing the
authorization model itself.

## What is NOT yet built (honest gaps)

- No frontend (Section 3)
- No task timeout tracking
- No general object-level lock across two workflows touching the same
  external object (only competing *trigger types* are detected as conflicts)
- Deleting a `Dependency` row is not defended against — see the crash-test
  report and `README.md#known-limitations`
