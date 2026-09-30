# Architecture

## What Spark is, and is not

Spark Personal OS is the **human-facing operational workspace** for Project 10
of the NYAYA-SATYA system. It aggregates, organizes, and explains information
produced by upstream specialized engines (Evidence Dependency, Procedural
Obligation, Case Continuity, Case Bottleneck, Hearing Readiness, Legal-Aid
Handoff, Registry Defect, Undertrial Liberty Sentinel, Deadline Guardian,
Workflow Autopilot).

Spark **never**:
- makes legal decisions, predicts outcomes, or scores legal risk
- invents dates, obligations, or registry requirements
- auto-approves consequential actions
- auto-submits filings or auto-contacts authorities
- reinterprets an upstream engine's conclusion as a legal fact

Spark **only**:
- stores and displays `EngineEvent`s emitted by upstream engines, with full
  provenance (`source_engine`, `source_entity`, `provenance_refs`)
- derives *operational attention* (not legal risk) from those events
- tracks personal/case tasks, deadlines, reviews, approvals, and changes that
  reference that upstream data
- requires an explicit human decision (`decide`, `acknowledge`, `dismiss`,
  `approve`/`reject`) for anything consequential

## Data flow

```
Upstream engines (EngineEvent, DEMO stub in Section 1/2)
        │
        ▼
CaseAttentionItem / Deadline / CaseChange / ReviewTask  (provenance preserved)
        │
        ▼
Task / Notification / ApprovalRequest / ActivityEvent   (human-scoped)
        │
        ▼
REST API (FastAPI, RBAC-enforced per case membership)
        │
        ▼
Frontend workspace (React) — "My Workspace" / "Case Workspace"
```

## Backend layout

```
backend/app/
  core/       settings, JWT + password hashing
  db/         SQLAlchemy session/engine, DEMO seed script
  models/     SQLAlchemy ORM models + enums (full domain model, see below)
  schemas/    Pydantic request/response schemas
  services/   RBAC (access.py), audit logging, LLMProvider abstraction
  api/        FastAPI routers: auth, cases, attention, tasks, deadlines,
              reviews, approvals, misc (changes/notifications/saved views/
              search/audit/digest/workspace summary)
```

## RBAC model

- Roles: `citizen`, `legal_aid`, `paralegal`, `advocate`, `admin`.
- Case-level access is governed by explicit `CaseMembership` rows, not by
  role alone — a role determines *what kind of actions* a user may take
  (e.g. only certain roles can decide approvals), but *which cases* a user
  can see is always membership-based (or `admin`, which sees all).
- Unauthorized case access returns `404`, not `403`, so the existence of a
  case a user cannot see is never leaked to them.
- All of this is enforced server-side in `app/services/access.py` and the
  route dependencies in `app/api/*` — never trust a client-side check alone.

## LLMProvider abstraction

`app/services/llm.py` defines an abstract `LLMProvider` with `MockProvider`,
`OpenAIProvider`, `AnthropicProvider`, and `GroqProvider` implementations.
`DEMO_MODE=true` (default) forces `MockProvider`, so the entire workspace —
attention, tasks, deadlines, reviews, approvals, search, digest — works with
**zero API keys**. AI is used only for optional narrative assistance (e.g.
phrasing a digest section); it is never in the critical path for computing
attention priority, deadlines, or approval state, which are all derived from
stored structured data only.

## Section plan (this repository is built incrementally, same repo throughout)

1. **Section 1 (done):** scaffold, full domain model, auth + RBAC, LLMProvider
   abstraction, DEMO seed, first passing tests.
2. **Section 2:** Attention Engine scoring/lifecycle, Task dependency
   enforcement, Deadline/tracked-date views, mock upstream `EngineEvent`
   adapters.
3. **Section 3:** Reviews, Approvals, Recent Changes, Case Digest generation,
   Notifications with deduplication, Saved Views, Pinned Cases.
4. **Section 4:** Frontend workspace UI (My Workspace, Case Workspace, Case
   Switcher, Command Palette, Calendar, Global Search, explainability
   panels) wired to the backend, plus final test pass and docs polish.
