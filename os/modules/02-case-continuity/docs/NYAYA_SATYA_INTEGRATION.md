# NYAYA-SATYA Integration Contract

**Status: contract definition only. No integration code exists in this repository.**
This project (Case Continuity Engine) is standalone and does not import from,
call into, or depend on NYAYA-SATYA or any other project. This document
defines the *shape* of a future integration, so that NYAYA-SATYA (or any
other consumer, including Project 01 / Hearing Readiness Engine) can plug
into this engine without either side being tightly coupled to the other's
internals.

Future NYAYA-SATYA menu entry:

```
NYAYA-SATYA
 └── 🔄 Case Continuity Engine
```

## Why a contract, not a coupling

Section 3 and section 57 of the build spec are explicit: this engine owns
**case state evolution** ("what is the current state, what changed, what's
unresolved, what's next"), while a consumer like the Hearing Readiness
Engine owns a *different* question ("is this case ready for its next
hearing"). The contract below is the seam between those two concerns.

## INPUT

A consumer integrates by supplying:

| Field | Type | Notes |
|---|---|---|
| `case_id` | string | The Case Continuity Engine's own case id, OR |
| external case reference | string | if NYAYA-SATYA has its own case identifier scheme, a future mapping table (`external_case_ref -> case_id`) is needed - **not implemented here**, left as a NYAYA-SATYA-side concern |

Optionally, a consumer may also push raw artifacts for ingestion via the
existing `POST /api/cases/{case_id}/ingest` endpoint - no new endpoint is
required for that direction.

## OUTPUT

Everything a consumer needs is already exposed by the REST API in this
repository (see `backend/app/routers/`). The stable contract surface is:

| Concern | Endpoint | Shape |
|---|---|---|
| Current State | `GET /api/cases/{id}/state` | snapshot + freshness |
| State Versions | `GET /api/cases/{id}/versions` | list of `{version_number, label, created_at, freshness}` |
| State Diff | `GET /api/cases/{id}/diff?from=X&to=Y` | structured diff (added/removed/changed per entity collection) |
| Events | `GET /api/cases/{id}/events` | append-only event history |
| Conflicts | `GET /api/cases/{id}/conflicts` | unresolved + resolved contradictions |
| Stale Signals | `GET /api/cases/{id}/state` (`freshness` field) + `GET /api/cases/{id}/continuity-health` | explainable freshness/health categories, never a bare score |
| Handoff Context | `POST /api/cases/{id}/handoff` | structured "what the next human/agent needs to know" |
| Provenance | embedded in every Event/StateChange/Conflict via `source_event_id` / `provenance` fields | resolvable via `GET /api/cases/{id}/events` |
| Audit Records | `GET /api/cases/{id}/audit` | append-only audit trail + agent run history |

All of these are read-only from a consumer's point of view. A consumer
(such as a future Hearing Readiness Engine) should treat this engine as the
**source of truth for case state** and never attempt to write to its tables
directly - it should either call `POST /api/cases/{id}/ingest` with a new
artifact, or (for human decisions) `POST /api/cases/{id}/proposals/{id}/review`.

## Versioning and stability

This contract targets the API surface as implemented in this repository at
this commit. No API versioning scheme (e.g. `/v1/`) has been added yet -
**NOT IMPLEMENTED**. Before a real NYAYA-SATYA integration ships, the
recommended next step is to prefix these routes with a version segment and
publish an OpenAPI schema (FastAPI generates one automatically at
`/openapi.json` in the meantime, which can be used as a starting point for
a generated client).

## Explicitly out of scope for this contract

- Authentication/authorization between NYAYA-SATYA and this engine -
  **NOT IMPLEMENTED**. This repo's own access model is a case-scoped,
  single-tenant demo (see `README.md`'s Security section).
- Any shared database or shared process - the two systems are expected to
  communicate over HTTP only.
- Any UI-level embedding (iframe, module federation, etc.) - out of scope
  for a backend integration contract.
