# Evaluation Lab

`backend/app/services/evaluation_service.py`, exposed at
`GET /api/cases/{case_id}/evaluation`. Every result is `PASS`, `FAIL`, or
`NOT_RUN` -- never a percentage, a score, or an invented accuracy number.
`NOT_RUN` means the case doesn't currently have the data needed to
exercise that check (e.g. no relationships at all yet), not that the
check failed.

## The six checks, exactly as implemented

1. **`provenance_completeness`** -- for every `EvidenceItem`, either
   `source_location_known=True` with an actual `page_number` or `section`
   set, or `source_location_known=False` (an honest "unknown," not a
   silent gap). `NOT_RUN` if the case has no evidence yet.
2. **`claim_traceability`** -- every `EvidenceRelationship` edge with
   `source_type=EVIDENCE, target_type=CLAIM` references an evidence ID
   that actually exists in this case. `NOT_RUN` if there are no such edges.
3. **`issue_mapping_coverage`** -- every edge with
   `source_type=CLAIM, target_type=ISSUE` references a claim ID that
   actually exists. `NOT_RUN` if there are no such edges (which is also
   the state of a case before any Issue Mapping proposal has been
   approved -- see `docs/agent-system.md`).
4. **`dependency_consistency`** -- every relationship's source and target
   IDs resolve to a real row of the declared type, and all of them belong
   to this case. Catches any edge that would otherwise silently point at
   nothing (or, worse, at another case's data).
5. **`case_isolation`** -- a defense-in-depth check: queries the evidence
   table for rows with this case's IDs but a *different* `case_id`, which
   should always return zero. This runs even when the case has evidence,
   as a live regression check rather than a one-time test.
6. **`contradiction_detection`** -- for every `CONTRADICTS` edge in the
   case, confirms `DependencyGraph.contradiction_edges_for()` actually
   finds it when queried for that edge's target. `NOT_RUN` if there are no
   `CONTRADICTS` edges yet.

## Why these six and not more

These are the checks that can be verified purely from structural
properties of stored rows -- no external ground truth is needed, so a
`PASS` here is a real guarantee, not a self-reported one. Checks that
would need a labeled "correct answer" dataset (e.g. "did the model extract
the *right* evidence") are out of scope for an automated, deterministic
lab and are instead covered by the anti-fabrication *code-level*
guarantee (every extracted excerpt is asserted to be a substring of the
source text) rather than a judged quality score.

## Response shape

```json
{
  "case_id": "...",
  "checks": {
    "provenance_completeness": "PASS",
    "claim_traceability": "NOT_RUN",
    "issue_mapping_coverage": "NOT_RUN",
    "dependency_consistency": "PASS",
    "case_isolation": "PASS",
    "contradiction_detection": "NOT_RUN"
  },
  "summary": {"pass_count": 3, "fail_count": 0, "not_run_count": 3}
}
```

## Verified by

`tests/api/test_api_flows.py::test_evaluation_lab_runs_on_demo_case` --
runs the lab against seeded Demo Case A and asserts every value is one of
the three allowed strings and that `fail_count == 0` on known-good demo
data.

## Known gap

Section 2 added a large amount of new surface (documents, agents, Time
Machine, RBAC) that the Evaluation Lab does not yet have checks for --
see `docs/status.md`'s "Not yet built" list, item 6, for the specific
proposed additions (e.g. confirming every gated agent action has a
corresponding `ReviewTask`).
