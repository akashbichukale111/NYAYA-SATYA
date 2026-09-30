# Domain model

All entities live in `backend/app/models/orm.py`; all controlled
vocabularies live in `backend/app/models/enums.py`. This document explains
the *why* behind each; for field-by-field detail, read the ORM file
directly -- it's short and the column names are self-explanatory.

## Entities implemented in this pass

| Entity | Purpose | Notably NOT implemented (yet) |
|---|---|---|
| `Case` | Top-level isolation boundary. `is_demo` flag, `owner_user_id` for RBAC. | multi-user collaborator lists |
| `User` | Minimal identity record (`email`, `role`). | login/password, sessions |
| `Document` | An uploaded file: hash, MIME, type, status. | virus scanning |
| `EvidenceItem` | A discrete piece of evidence, with provenance fields (`page_number`, `section`, `source_location_known`) that are never fabricated -- `source_location_known=False` is a valid, expected, and common state. | full temporal-validity enforcement (`valid_from`/`valid_until` columns exist but nothing yet rejects an out-of-window evidence item automatically -- that's a human/reviewer judgment call by design) |
| `Claim` | A factual proposition, always traceable to originating evidence via `EvidenceRelationship`. | NLP-based claim clustering/deduplication |
| `Issue` | A question that matters to the case. | issue hierarchies (sub-issues) |
| `EvidenceRelationship` | Generic polymorphic edge (see docs/dependency-engine.md). | edge versioning (an edge's own change history isn't snapshotted -- only EvidenceItem is) |
| `Conflict` | A flagged pair of contradictory nodes. | automatic resolution of any kind |
| `ReviewTask` | A proposed, not-yet-applied change (Human Legal Gate). | task assignment/notifications |
| `AuditEvent` | Append-only log row. | log export/retention policy |
| `EvidenceVersion` | Append-only snapshot of one `EvidenceItem` at one point in time (Time Machine). | equivalent versioning for `Claim`/`EvidenceRelationship` |
| `CrashTestRun` | A persisted, non-destructive simulation result. | scheduled/batch crash-test sweeps |

## Uncertainty is a first-class citizen

Two enums carry the product's core epistemic stance and are used
everywhere instead of booleans:

- `EvidenceState` (`UNKNOWN`, `USER_REPORTED`, `DOCUMENT_SUPPORTED`,
  `PARTIALLY_SUPPORTED`, `SUPPORTED`, `CONTRADICTED`, `CONFLICTING`,
  `UNVERIFIED`, `SUPERSEDED`, `EXCLUDED`, `MISSING`,
  `REQUIRES_HUMAN_REVIEW`)
- `VerificationStatus` (`UNVERIFIED`, `PENDING_REVIEW`, `VERIFIED`,
  `REJECTED`, `REQUIRES_HUMAN_REVIEW`)

No code path in this repository silently converts an uncertain state into
a certain one. The only way `VerificationStatus.VERIFIED` gets set on a
row is through `review_service.decide(..., approve=True)`, which is only
reachable via a human calling `POST /api/reviews/{id}/approve` with role
`>= ADVOCATE`. Agents can *recommend* verification (`VerificationAgent`)
but cannot apply it.

## Why `EvidenceRelationship` isn't three separate edge tables

An earlier design would have needed `EvidenceClaimLink`,
`ClaimIssueLink`, `EvidenceEvidenceLink`, etc. -- multiplying with every
new node-type pair the spec calls for (Evidence↔Evidence, Claim↔Claim,
Claim↔Issue, Evidence↔Issue, Issue↔Issue). Instead there is one table
with polymorphic `source_type`/`source_id`/`target_type`/`target_id`
columns and a `relationship_type` from `RelationshipType`. This is what
lets `graph_service.DependencyGraph` build one adjacency structure and
traverse the whole Evidence→Claim→Issue graph (plus lateral edges) with a
single BFS implementation instead of N special-cased traversals.

## Case isolation as a structural property

Every entity except `User` carries a `case_id` foreign key, and every
service/API function that queries one of these tables filters by
`case_id` (see `docs/security.md` for how this is tested). There is no
"global" query path in the codebase that would let one case's data leak
into another's response.
