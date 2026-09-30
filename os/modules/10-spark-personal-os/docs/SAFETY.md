# Safety Boundary

Spark Personal OS is an **operational workspace**, not a legal authority.
This document is the enforceable contract for what the system is allowed to
say and do. Any pull request that violates this contract should be rejected
in review.

## Hard boundaries (must never happen)

The system MUST NOT:
- make or imply a legal decision, outcome prediction, bail prediction, or
  guilt/innocence determination
- invent a deadline, obligation, or registry requirement that was not
  explicitly stated by an upstream source (`SOURCE_STATED`, `USER_ENTERED`,
  `SYSTEM_DERIVED` with a visible derivation, or `UNKNOWN` — never silent)
- auto-submit a legal filing or auto-contact an authority
- silently auto-approve a consequential action — every `ApprovalRequest`
  requires an explicit human `approve`/`reject`/`request_clarification`
- convert an engine warning into a legal conclusion, e.g. turning
  "evidence verification pending" into "this case will fail"

## Required, not optional

Every `CaseAttentionItem`, `Deadline`, `CaseChange`, and `ReviewTask` MUST
retain: `source_engine`, `source_entity`, `case_id`, a provenance reference,
`status`, timestamps, and (where applicable) an explicit uncertainty/review
state (`requires_human_review`).

Every attention item MUST be explainable via the "Why is this here?" panel:
source, what changed, affected entity, provenance, current status,
dependencies, safe next action, and whether human review is required.
**No unexplained alerts.**

## Approved phrasing patterns

Allowed (operational, provenance-linked, non-conclusory):
- "Three cases have unresolved human-review items."
- "Case C-102 changed since your last review."
- "A source-stated hearing date is approaching."
- "Evidence verification is pending."

Disallowed (legal conclusion / prediction):
- "This case will fail."
- Any statement of bail likelihood, guilt/innocence, or case outcome.

## Enforcement in this codebase

- `AttentionPriority` values are operational only (`INFO`, `ATTENTION`,
  `HIGH_ATTENTION`, `REQUIRES_HUMAN_REVIEW`) — there is intentionally no
  "legal risk score" field anywhere in the schema.
- `DateSourceType` is required on every date-bearing record so a UI can never
  present a derived or unknown date as if it were authoritative.
- `ApprovalRequest.status` only transitions via an explicit decision
  endpoint (`POST /api/approvals/{id}/decide`) called by an authenticated
  human; there is no code path that transitions it automatically.
- Case Digest (`GET /api/cases/{id}/digest`) is generated only from stored
  structured fields already present on the case's records — see
  `test_case_digest_has_no_hallucinated_free_text_field` in
  `backend/tests/test_workspace.py`, which is a regression test for this
  boundary and must keep passing.
