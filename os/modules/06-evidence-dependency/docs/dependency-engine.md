# Dependency engine

The core differentiator: an explicit Evidence → Claim → Issue graph built
from stored rows, with real traversal answering "what supports this" and
"what breaks if this disappears."

## Where it lives

`backend/app/services/graph_service.py` (traversal + metrics) and
`backend/app/services/impact_service.py` (impact analysis + crash test).
Both are pure functions of the database -- no cached state, no
approximations, no invented numbers. Every request rebuilds the graph
from `EvidenceRelationship` rows.

## The graph model

One generic, polymorphic edge table (`EvidenceRelationship`) instead of N
join tables:

```
source_type, source_id  →  relationship_type  →  target_type, target_id
```

`source_type`/`target_type` are each one of `EVIDENCE | CLAIM | ISSUE`, so
the same table carries Evidence→Claim, Claim→Issue, Evidence→Evidence
(e.g. `SUPERSEDES`), Claim→Claim, Evidence→Issue, and Issue→Issue edges
without schema changes.

`DependencyGraph` (`graph_service.py`) loads all active edges for a case
once per request and builds forward/backward adjacency dicts keyed by
`(type, id)`. This is intentionally simple (Python dict traversal, not a
graph database) -- fine at demo/case scale; see docs/status.md for the
scaling note if this ever needs to handle thousands of nodes.

## What counts as "support" for traversal

`SUPPORT_LIKE = {SUPPORTS, PARTIALLY_SUPPORTS, CORROBORATES, REQUIRES,
DEPENDS_ON}` -- these are the edge types `downstream_impact()` follows
when asking "what depends on this node." `CONTRADICTS` is tracked
separately (`NEGATIVE_LIKE`) and never treated as support.

## Independence, not just difference

`independent_source_count()` counts **distinct upstream `document_id`
values**, not distinct evidence rows. This is a direct implementation of
the brief's instruction: two evidence items extracted from the same PDF
are not independent corroboration just because they're different
`EvidenceItem` rows. An evidence item with no `document_id` (manually
entered, not tied to any document) counts as its own independent source.
This same rule is reused by the Relationship Agent (Section 2) to decide
when a second SUPPORTS edge should be reclassified as CORROBORATES.

## Coverage metrics (`coverage_metrics`)

Every number is computed by walking the graph for the current case, on
every call:
- `claims_with_evidence` / `claims_without_evidence`
- `issues_with_supporting_claims` / `unsupported_issues`
- `conflicting_claims` -- claims with at least one incoming CONTRADICTS edge
- `single_source_claims` -- claims where `independent_source_count == 1`
- `verified_evidence_items` / `unverified_evidence_items`

No caching, no denormalized counters -- these are always freshly derived
from the live edge table, so they can never drift out of sync with reality.

## Fragility report (`fragility_report`)

For every evidence item in the case, runs `downstream_impact()` and
classifies criticality:
- `NONE` -- nothing depends on it
- `LOW` -- 1-2 claims/issues affected
- `MODERATE` -- 3+ affected
- `SINGLE_POINT_DEPENDENCY` -- at least one affected claim has
  `independent_source_count == 1`, i.e. this evidence item is that
  claim's *only* support

Sorted descending by affected-node count, so the riskiest evidence surfaces
first. This is what the Command Center's "Critical Dependencies" section
and the NYAYA-SATYA `integration-summary` endpoint both read from.

## Missing-evidence report (`missing_evidence_report`)

Four buckets, each a real query result, never invented:
- `claims_without_evidence` -- no incoming support edge at all
- `claims_with_only_conflicting_evidence` -- no support, but a
  CONTRADICTS edge exists
- `claims_with_single_source_only` -- supported, but fragile
- `issues_without_supporting_claims`

## Impact analysis (`impact_service.compute_impact`)

Real-time version of the same traversal, scoped to one node
(`GET /evidence/{id}/impact`, `GET /claims/{id}/impact`). Returns
`affected_claims`, `affected_issues`, a `criticality` label (same four
levels as fragility), and `human_review_required` (true whenever
criticality isn't `NONE`).

## Evidence Crash Test (`impact_service.run_crash_test`)

Simulates one of 10 event types (see `docs/agent-system.md` /
`CrashTestEventType` in `app/models/enums.py`) by computing before/after
coverage and the real downstream impact, then persisting a
`CrashTestRun` row. **It never mutates `EvidenceItem`, `Claim`, `Issue`,
or `EvidenceRelationship`** -- verified by
`tests/unit/test_crash_test.py::test_crash_test_is_non_destructive`,
which asserts the target evidence row is byte-for-byte identical before
and after a `REMOVE_EVIDENCE` simulation. `human_review_required` is
always `True` on a crash-test result -- a simulation is informational,
never authorization to act.

## What this engine deliberately does not do

It never assigns a probability of legal success, never says which side of
a contradiction is "true," and never auto-resolves a conflict. Every
output is phrased as a structural fact about the graph ("N claims lose
support," "this evidence is a single point of dependency") plus, where
relevant, `REQUIRES_HUMAN_REVIEW` -- never a legal conclusion.
