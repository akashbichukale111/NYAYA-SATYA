# Defect Engine

Code: `backend/app/services/defect_engine.py`,
`backend/app/services/precheck.py`.

## Taxonomy

`DefectType` in `backend/app/core/enums.py` implements the full taxonomy
from the spec (Completeness, Document Quality, Metadata, Version, Registry
Feedback, Reference Integrity, Provenance, Security). `DEFECT_CATEGORY_MAP`
derives the category from the type so a defect can never be miscategorized
by hand.

## Severity ≠ legal consequence

`DefectSeverity` is `INFO | ATTENTION | HIGH_ATTENTION |
REQUIRES_HUMAN_REVIEW`. Every description template in `defect_engine.py`
was written to describe only what was detected and what's missing —
grep the file for "reject" or "invalid" and you will not find either word
used to describe an outcome. The one place "reject" appears is in the
description of a security-scan defect, describing that the document's
content was *not* used to make a determination.

## Evidence linking

Every defect-creating function takes an `evidence` list and writes
`DefectEvidence` rows carrying `document_version_id` / `section_id` /
`requirement_id` / `excerpt` / `location_known` / `location_label`.
`location_label` is only ever populated (e.g. `"page 3"`) when the
originating `DocumentSection.location_known` is `True` — see
`generate_defects_from_attachment_references()`.

## Lifecycle

`DefectLifecycleState`: `DETECTED → TRIAGED → HUMAN_REVIEW → CONFIRMED →
ACTION_REQUIRED → CORRECTION_SUBMITTED → VERIFIED → RESOLVED`, with
`REJECTED / FALSE_POSITIVE / DUPLICATE / UNKNOWN / BLOCKED` as
alternatives.

As of this build, the only state transition wired into the API is the
review gate: `DETECTED → CONFIRMED` or `DETECTED → REJECTED`
(`backend/app/routers/review.py::_apply_decision`). The
`ACTION_REQUIRED → CORRECTION_SUBMITTED → VERIFIED → RESOLVED` tail is
represented in the domain model and exercised by the demo seed script
(Demo C) but does not yet have a dedicated API endpoint to drive it
generically — see `docs/correction-workflow.md` for what exists today and
Section 2/3 for what's planned.

## Precheck is idempotent, not cumulative

`run_precheck()` deletes only `DETECTED`-status defects before
regenerating, so re-running precheck after nothing has changed produces
the same set of defects rather than duplicating them, and never touches a
defect a human has already triaged past `DETECTED`.
