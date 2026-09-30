# Privacy

## Roles and least privilege

`UserRole`: `CITIZEN`, `LEGAL_AID`, `ADVOCATE`, `ADMIN` (`app/core/enums.py`).
Read access is currently uniform across roles within a case for simplicity
in this build; write/review/export actions are gated by
`require_min_role()` (see `docs/security.md`). Field-level redaction by role
(e.g. hiding a person's full identifying details from a `CITIZEN` role) is
**not yet implemented** — tracked as a gap, not silently assumed solved.

## Case isolation as a privacy control

Because every query is scoped through `get_case_or_404()`, a valid entity ID
from Case A can never be used to read data belonging to Case B — the API
returns 404 rather than leaking existence. This is the primary technical
control preventing cross-case data exposure today.

## What must never leak

Per the master spec, sensitive personal information must not leak through
APIs, graph queries, search, URLs, frontend state, exports, or logs.
Current state:
- **APIs / graph queries**: case-scoped as above.
- **URLs**: entity IDs are opaque UUIDs, not sequential/guessable.
- **Logs**: `AuditEvent.details` stores structured metadata (status changes,
  note text) rather than full document text, limiting log exposure surface.
- **Exports**: no export/publication endpoint exists yet in this build, so
  there is currently no export-path leakage risk, but also no export feature
  to test against `EXPORT_APPROVAL`'s review-gate requirement — noted as a
  gap.

## Untrusted document content

Uploaded documents are stored as-is (with SHA-256 recorded) and their
extracted text is only ever pattern-matched, never rendered as HTML/executed
— eliminating a stored-XSS-via-document-text vector in the current
implementation, since the frontend renders extracted snippets as plain text
via React (which escapes by default), not raw HTML.
