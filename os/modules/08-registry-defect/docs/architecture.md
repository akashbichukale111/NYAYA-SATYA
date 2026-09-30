# Architecture

## Layers

```
Frontend (React)  →  REST API (FastAPI routers)  →  Services (engines)  →  SQLAlchemy models  →  SQLite/Postgres
```

- **`backend/app/models/`** — the SQLAlchemy domain model. Every
  case-scoped table carries `case_id`. Enums are stored as plain strings
  (not native DB enum types) so adding a new status value never requires a
  migration, and an unrecognized value fails loudly rather than silently
  coercing.

- **`backend/app/services/`** — the actual detection logic, framed as the
  spec's "agents" (see `docs/agent-system.md`). Each service takes a
  `Session` and case/package ids and returns/persists structured rows. No
  service call ever mutates data outside the `case_id` it was given.

- **`backend/app/routers/`** — thin FastAPI route handlers. Every
  handler: (1) resolves the target entity, (2) calls
  `assert_case_access` to enforce case isolation, (3) calls
  `require_capability` where the action is role-gated, (4) delegates to a
  service, (5) writes an audit record. See `backend/app/core/security.py`
  and `backend/app/core/audit.py`.

- **`backend/app/main.py`** — wires routers, CORS, and two exception
  handlers: `AccessDenied` → 403 with a consistent JSON shape, and a
  catch-all → 500 with a consistent JSON shape that never leaks a stack
  trace to the client.

- **`frontend/src/lib/api.ts`** — the single typed client for the backend.
  Every field returned by the API is typed to match
  `backend/app/schemas.py` exactly; there is deliberately no
  frontend-side data synthesis (no client-side "looks about right"
  fallback values).

## Precheck pipeline

`POST /api/filing-packages/{id}/precheck` runs, in order (see
`backend/app/services/precheck.py`):

1. Clear only `DETECTED`-status defects (never touches defects a human has
   already triaged past that state).
2. Resolve attachment references against current package documents.
3. Rebuild the checklist against current requirements/documents.
4. Detect metadata conflicts.
5. Detect duplicates.
6. Generate defects from: checklist gaps, unresolved attachment
   references, metadata conflicts, duplicates, document quality issues,
   security scan hits, and open registry objections.
7. Advance the filing package's lifecycle state to `REVIEW_REQUIRED` (if
   any open defects) or `READY_FOR_HUMAN_REVIEW` (if none) — never further
   than that automatically.
8. Create a `ReviewTask` for every newly generated defect.

This is non-destructive and idempotent: running it twice in a row with no
underlying changes produces the same defect set (verified by
`backend/tests/test_reasoning_flows.py`).

## Why SQLite now, Postgres later

`backend/app/core/database.py` reads `DATABASE_URL` from the environment
and falls back to a local SQLite file. No model or query uses a
SQLite-only construct (no `JSON1` extension functions, no `ROWID` tricks) —
switching `DATABASE_URL` to a Postgres DSN is the only change required.
This has not yet been tested against a live Postgres instance in this
build; it is a design property, not a verified migration.
