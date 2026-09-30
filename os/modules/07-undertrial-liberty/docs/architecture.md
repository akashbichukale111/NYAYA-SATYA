# Architecture

## Safety boundary (read this first)

Undertrial Liberty Sentinel is a **procedural liberty-event visibility tool**,
not a legal decision system. It never determines guilt, predicts bail
outcomes, calculates statutory deadlines, or takes autonomous legal action.
Every status label in the system is one of: `SOURCE_FACT`, `USER_REPORTED`,
`SYSTEM_DERIVED`, `UNVERIFIED`, `CONFLICTING`, `UNKNOWN`, or
`REQUIRES_HUMAN_REVIEW` (`app/core/enums.py::VerificationStatus`). Nothing in
the system is allowed to collapse that uncertainty into a legal conclusion.

## High-level flow

```
Document upload
   → Secure ingestion (hash, MIME/ext validation, quarantine)
   → Text extraction (PDF/DOCX/TXT/JSON/CSV)
   → Rule-based extraction agents (custody / hearing / order / bail / release)
   → Reconciliation agent (conflict detection)
   → Liberty Attention Engine (operational attention items)
   → Dependency graph rebuild
   → Case snapshot (Time Machine)
```

## Backend layers

- `app/models/orm.py` — SQLAlchemy models, one per domain entity in the spec.
- `app/core/` — cross-cutting concerns: config, RBAC/security, document
  ingestion, LLM provider abstraction, evaluation suite.
- `app/agents/` — the "multi-agent system": each file is a bounded, testable
  unit (extraction, reconciliation, attention, dependency, digital_twin,
  time_machine, simulation, governance). None of these agents can take a
  consequential action on their own — every write of a legally-sensitive
  field routes through `app/agents/governance.py`'s review-task mechanism.
- `app/api/` — FastAPI routers, one per functional area, matching the
  spec's endpoint list.

## Why Simulation/Crash Test uses a database SAVEPOINT

`app/agents/simulation.py` needs to show "what would happen if X" using the
*real* attention/dependency/reconciliation logic (not a separate, possibly
inconsistent, mock implementation) while guaranteeing the mutation never
touches production data. It does this with `db.begin_nested()` (a SQL
SAVEPOINT), applies the mutation, recomputes derived state, captures the
result, and always rolls back in a `finally` block. See
`docs/PROJECT_STATUS.md` for a real bug that was found and fixed in this
mechanism, and why every agent function that can be called from inside a
SAVEPOINT takes an explicit `commit: bool` parameter.

## Frontend

React + TypeScript + Vite + Tailwind + TanStack Query. `src/api/client.ts` is
a thin typed wrapper over every backend endpoint. Pages read live data only —
DEMO mode is a property of the *backend* seed data, not a frontend mock path.
