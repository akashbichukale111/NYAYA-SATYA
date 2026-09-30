# NYAYA-SATYA Integration Contract

**Status: planned interface, not yet wired to any parent platform.** The
Hearing Readiness Engine (HRE) is fully standalone today. This document
specifies the contract a future NYAYA-SATYA shell would use to embed it,
so that work can happen later without changing HRE's internals.

## Why a contract, not a coupling

Section 46/47 of the build brief are explicit: HRE must not be tightly
coupled to NYAYA-SATYA, which does not exist yet as a running system.
Everything below is therefore a **specification of the boundary**, backed
by API routes that already exist and already return exactly this shape —
not a promise about a system on the other side of it.

## The contract

```
Case Input
  -> Hearing Readiness Analysis   (POST /api/cases/{id}/readiness/run)
  -> Readiness State              (GET  /api/cases/{id}/readiness)
  -> Blockers                     (GET  /api/cases/{id}/blockers)
  -> Evidence References          (GET  /api/cases/{id}/evidence)
  -> Suggested Actions            (GET  /api/cases/{id}/actions)
  -> Verification Results         (embedded in Action.result / GET .../actions)
  -> Audit Records                (GET  /api/cases/{id}/audit)
```

### Case Input

A parent platform would create a case via `POST /api/cases` with
`{title, case_type, parties}`, then ingest documents via
`POST /api/cases/{id}/documents` (multipart file upload). HRE owns all
downstream Requirement/Evidence/Blocker modeling from there — the parent
platform does not need to understand HRE's internal domain model, only
these input/output shapes.

### Every response already carries what a menu-embedding shell needs

- `overall` / `categories` readiness state, never a bare percentage
  (section 6/31 compliance) — safe to render as a status chip in a
  parent shell's case list without re-deriving anything.
- Every blocker carries `severity`, `downstream_impact`, and
  `suggested_safe_action` — enough for a parent dashboard to show
  "N blockers, highest severity X" without a second round trip.
- Every action requires human approval inside HRE
  (`POST /api/cases/{id}/actions/{action_id}/approve`) before anything
  consequential happens — a parent platform embedding HRE inherits this
  safety property for free; it cannot accidentally bypass the gate by
  calling a different endpoint, because no such endpoint exists.

### Identity and multi-tenancy (planned)

This build has no auth layer (single implicit demo user, matching
section 40's "must run without external setup"). A production embedding
would need:
- A `tenant_id` / `org_id` column added to `Case` (schema is additive,
  not a breaking change).
- Bearer-token or session auth on every route, validated by the parent
  platform's identity system, passed through as a header HRE trusts.
- `approved_by` on `Approval` already exists and is free-text; a real
  integration would populate it from the parent platform's authenticated
  user rather than the current hardcoded `"demo_user"` default.

### Event/webhook surface (planned, not implemented)

Not built in this submission. The natural extension point is
`services/audit_service.log_event()` — every state-changing operation
already funnels through one function, so adding an outbound webhook or
message-queue publish there would notify a parent platform (or the other
NYAYA-SATYA modules listed in section 47) without touching any other
service.

### Explicitly out of scope for this submission

- Case Continuity Engine, Case Bottleneck Engine, Legal-Aid Handoff,
  Procedural Obligation Engine, Evidence Dependency Engine, Undertrial
  Liberty Sentinel, Registry Defect Agent, Case Crash Test (platform-wide),
  Case Operations OS, Deadline Guardian, Workflow Autopilot — none of
  these are implemented here. HRE's own case-level Crash Test (section 16)
  is a different, narrower thing: adversarial mutation testing of one
  case's readiness computation, not a platform-wide chaos-testing module.
