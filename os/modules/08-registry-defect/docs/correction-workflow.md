# Correction Workflow

Code: `backend/app/models/__init__.py::CorrectionRequest,
CorrectionSubmission`, `backend/app/routers/defects.py`.

## What a correction is here

A `CorrectionRequest` records: what's wrong (via `defect_id` and/or
`objection_id`), a plain-language `description`, and an optional
`suggested_action` (one of the `ActionProposalType` values, e.g.
`ATTACH_MISSING_REFERENCE`). Creating one is a planning act — it does not
touch any document or filing state.

A `CorrectionSubmission` represents actually attaching evidence of the fix
(e.g. a newly uploaded document version) to a `CorrectionRequest`.
**Every `CorrectionSubmission` in this codebase carries `simulated=True`
by construction** (see `seed_demo.py::seed_demo_c`) — there is no code
path that submits anything to a real external registry. "Submission" here
means "recorded in this system as done," which is exactly what the spec's
"Submit correction in simulation" flagship-flow step means.

## Verification, not auto-resolution

A `Verification` row (`target_type=CORRECTION`) is created alongside a
submission with `result=PENDING`. **Nothing in this codebase
automatically flips a `Verification` to `VERIFIED`** — the spec is
explicit that a defect must never be marked resolved merely because a
file changed; a verification pass has to actually re-run detection logic
and confirm the underlying condition no longer holds. That re-check engine
(a dedicated `Verification Agent` per the spec) is planned for Section 2.

## Current gaps

- No API endpoint yet to create a `CorrectionSubmission` directly (only
  the demo seed script does it, for illustration). The
  `POST /api/filing-packages/{id}/corrections` endpoint creates the
  `CorrectionRequest` only.
- No automatic re-verification loop yet — see `docs/defect-engine.md`
  "Lifecycle" section.
