# Requirement Engine

Code: `backend/app/services/requirement_engine.py`.
Tests: `backend/tests/test_requirement_engine.py`.

## The source principle, enforced in code

`create_requirement()` branches on `source`:

- `USER_PROVIDED_CHECKLIST`, `SOURCE_DOCUMENT`, `AUTHORIZED_TEMPLATE`,
  `CONFIGURED_REGISTRY_RULE`, `IMPORTED_REQUIREMENT_SET` →
  `status=ACTIVE`, `verification_status=SOURCE_SUPPORTED`.
- `UNKNOWN` with no `source_reference` → `status=UNKNOWN`,
  `verification_status=UNKNOWN`. **This requirement will never be treated
  as active by the checklist engine** — it still gets a checklist row
  (so it isn't silently lost) but that row is forced to
  `REQUIRES_HUMAN_REVIEW` regardless of package contents.
- Anything else unrecognized → `status=REQUIRES_VERIFICATION`,
  `verification_status=REQUIRES_HUMAN_REVIEW`.

There is no code path in this file, or anywhere else in the codebase, that
sets `status=ACTIVE` or `verification_status=SOURCE_SUPPORTED` without one
of the five explicit, named sources above. This is the concrete mechanism
behind the "never invent a registry rule" rule in the top-level README.

## Provenance

Every created requirement gets a matching `ProvenanceRecord`
(`origin=USER_INPUT` if it came from a user-provided checklist, else
`origin=IMPORTED`), so "where did this rule come from" is always
answerable from the database, not just from the requirement row itself.

## What's deliberately NOT here yet

An `IMPORTED_REQUIREMENT_SET` import pipeline (e.g. parsing an official
registry rule document into `Requirement` rows automatically) is not
implemented. Building this without extreme care would risk exactly the
"invent a registry rule from LLM general knowledge" failure mode the spec
prohibits — any future importer must cite each imported requirement's
concrete source line, not synthesize one from a model's training data.
