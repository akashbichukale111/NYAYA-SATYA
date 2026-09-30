# Privacy

## Roles

`UserRole`: `CITIZEN`, `LEGAL_AID`, `ADVOCATE`, `ADMIN`
(`backend/app/core/enums.py`). Capabilities per role are defined in
`backend/app/core/security.ROLE_CAPABILITIES` and enforced server-side on
every request — the frontend has no independent enforcement and is not
trusted as a security boundary.

## Case A must never expose Case B

Enforced by `assert_case_access()` on every route (see
`docs/security.md`). This is tested directly, not just asserted: see
`backend/tests/test_api_cases.py::test_case_isolation_blocks_other_owner`
and `test_api_documents.py::test_document_upload_forbidden_across_case_isolation`.

## Sensitive metadata and identifiers

`DocumentMetadata` fields (case numbers, party names, dates, reference
numbers) are stored as plain values scoped to `case_id`, subject to the
same case-isolation enforcement as every other case-scoped table. There is
no cross-case metadata index or global search — a query for "all
documents with party name X" is not something this API can answer,
by design.

## What's not yet built

- Field-level redaction in exports/API responses for particularly
  sensitive identifiers (e.g. masking all but the last few digits of a
  reference number for a `CITIZEN`-role viewer). Currently, if a role can
  see a case at all, it sees full metadata values.
- Data retention/deletion policy and tooling. Nothing in this build
  deletes a case, document, or audit record — which is correct for
  audit integrity, but a real deployment will need an explicit, separately
  governed retention/erasure process for citizen data that this codebase
  does not yet implement.
