# Registry Objections

Code: `backend/app/models/__init__.py::RegistryObjection`,
`backend/app/routers/defects.py`,
`backend/app/services/defect_engine.py::generate_defects_from_objections`.

## Recording an objection

`POST /api/filing-packages/{id}/objections` takes `original_text` (stored
verbatim, never edited or paraphrased by any code path) and an optional
`source_reference` (e.g. "Registry letter dated 12 March"). It starts at
`status=OPEN`.

## Linking to a defect

The next `precheck` run creates an `UNRESOLVED_OBJECTION` defect for every
objection whose status is `OPEN`, `ACKNOWLEDGED`, or `CORRECTION_PLANNED`
and that doesn't already have a `linked_defect_id` — and sets that link, so
an objection is never turned into more than one defect across repeated
prechecks.

## Lifecycle

`ObjectionStatus`: `OPEN → ACKNOWLEDGED → CORRECTION_PLANNED →
CORRECTION_SUBMITTED → VERIFICATION_PENDING → RESOLVED`.

As of this build, `OPEN → CORRECTION_SUBMITTED` is driven manually (see
the Demo C seed script, `backend/app/services/seed_demo.py::seed_demo_c`,
which sets it directly alongside creating a `CorrectionRequest`). A
dedicated endpoint to transition an objection through its full lifecycle
via the API (rather than only being inferable from linked correction
state) is planned for a later section — see `docs/correction-workflow.md`.
