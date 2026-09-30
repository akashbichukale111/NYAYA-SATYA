# NYAYA-SATYA integration

This project is Project 06 in the NYAYA-SATYA pipeline:

```
Legal-Aid Handoff → Case Continuity → Procedural Obligation Engine →
Evidence Dependency Engine → Case Bottleneck Engine → Hearing Readiness
Engine → TARKA-VYUH → UNWIND Governance & Audit Core → Human Legal Gate
```

## Independence guarantee

`backend/app/` contains **zero imports referencing NYAYA-SATYA, TARKA-VYUH,
UNWIND, or any sibling module by name.** This is directly checkable:

```bash
grep -rn "nyaya\|tarka\|unwind" backend/app --include="*.py" -i
# -> only match is api/integration.py's own docstring describing this contract;
#    no import, no function call, no dependency on any sibling module
```

The engine can be deployed, run, and tested entirely on its own (which is
exactly what this repository's test suite does). Downstream modules
consume it through one HTTP endpoint and nothing else.

## The contract

`GET /api/cases/{case_id}/integration-summary` →

```json
{
  "case_id": "...",
  "evidence_count": 0,
  "claim_count": 0,
  "issue_count": 0,
  "unsupported_claims": 0,
  "unsupported_issues": 0,
  "conflicting_claims": 0,
  "critical_dependencies": [],
  "impact_items": [],
  "verification_pending": 0,
  "provenance_refs": [],
  "attention_items": [],
  "last_updated": "..."
}
```

This matches the master brief's specified shape exactly (see
`backend/app/schemas/schemas.py::IntegrationSummary` and
`backend/app/api/integration.py`). Field sources:

| Field | Computed from |
|---|---|
| `evidence_count`, `claim_count`, `issue_count` | `graph_service.coverage_metrics` totals |
| `unsupported_claims`, `unsupported_issues`, `conflicting_claims` | same coverage metrics |
| `critical_dependencies` | `graph_service.fragility_report`, filtered to `SINGLE_POINT_DEPENDENCY` |
| `impact_items` | top 10 entries from the same fragility report |
| `verification_pending` | count of `EvidenceItem` rows with `verification_status != VERIFIED` |
| `provenance_refs` | IDs of evidence items with `source_location_known=True` |
| `attention_items` | one entry per critical dependency, plus a `PENDING_HUMAN_REVIEW` entry if the review queue is non-empty |
| `last_updated` | current server timestamp at request time |

## What downstream modules should and shouldn't do with this

**Should**: use `critical_dependencies` and `attention_items` to decide
whether a case is ready to move to the next pipeline stage (e.g. the
Hearing Readiness Engine might block progression while
`unsupported_issues > 0`). Use `verification_pending` as a queue-depth
signal. Poll `last_updated` to detect staleness.

**Should not**: treat any field here as a legal conclusion. The engine
never computes a win-probability, a truth determination, or a
recommendation to proceed/not proceed -- that judgment belongs to a human
and, per the pipeline diagram, ultimately to the Human Legal Gate at the
end of the chain. This endpoint reports structural facts about the
evidence graph, nothing more.

## Auth for downstream callers

The integration-summary endpoint is subject to the same RBAC as every
other endpoint (`docs/security.md`) -- a downstream service calling it on
a case's behalf needs to send `X-User-Id`/`X-User-Role` headers for an
actor with access to that case (its owner, or `ADMIN`), or the case must
be `is_demo=True`. There is currently no service-to-service auth
mechanism (API key, mTLS) separate from the per-request actor headers --
a documented gap for a production integration.

## Verified by

`tests/api/test_api_flows.py::test_integration_summary_contract` asserts
every field listed above is present in the response and that a case with
a known single-point dependency (Demo Case B) actually surfaces it under
`critical_dependencies`.
