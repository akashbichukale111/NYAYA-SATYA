# NYAYA-SATYA Integration

Code: `backend/app/routers/integration.py`.

## Position in the chain

```
Legal-Aid Handoff → Case Continuity → Procedural Obligation →
Evidence Dependency → REGISTRY DEFECT ENGINE → Case Bottleneck →
Deadline Guardian → Hearing Readiness → Workflow Autopilot →
TARKA-VYUH → UNWIND Governance & Audit → Human Legal Gate
```

This module is the "Registry Defect Engine" box in that chain. It has no
code that calls outward to any other box — the relationship is
one-directional: NYAYA-SATYA (or anything else) can call this module's
summary endpoint; this module never calls out.

## The contract

`GET /api/integration/nyaya-satya/cases/{case_id}/summary` returns exactly
the shape specified in the master build brief:

```json
{
  "case_id": "...",
  "filing_packages": 0,
  "open_defects": 0,
  "high_attention_defects": 0,
  "missing_documents": [],
  "missing_references": [],
  "metadata_conflicts": [],
  "duplicate_groups": [],
  "open_objections": [],
  "corrections_pending": [],
  "verification_pending": [],
  "blocked_workflows": [],
  "attention_items": [],
  "provenance_refs": [],
  "last_updated": "..."
}
```

Every field is a plain count or a list of `{id, ...}` dicts pulled
directly from this database — `get_case_summary()` in
`integration.py` contains no synthesized judgment, no LLM call, and no
"compliance score." It is exactly as much of a legal-compliance verdict as
a row count is.

## Why it's safe to depend on

- **Read-only.** The route has no side effects — it only queries.
- **Case-isolated.** `assert_case_access()` is called before the query
  runs, same as every other endpoint.
- **Independently runnable.** Deleting `integration.py` and its one line
  in `main.py` removes NYAYA-SATYA awareness from this codebase entirely
  without breaking anything else — verified by inspection: no other file
  imports from `integration.py`.

## Verified

Exercised manually during development against a seeded case
(`case_id` from `/api/demo/seed`) and confirmed to return the correct
`open_defects` / `high_attention_defects` counts matching what
`/api/filing-packages/{id}/defects` showed for that case's packages.
