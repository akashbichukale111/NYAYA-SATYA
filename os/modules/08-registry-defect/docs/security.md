# Security

## Upload security

| Control | Implementation | Test |
|---|---|---|
| Extension allowlist | `parsing.ALLOWED_EXTENSIONS` | `test_parsing.py::test_parse_unsupported_format` |
| Dangerous-extension rejection | `security_scan.check_dangerous_extension`, enforced in `routers/documents.py` before parsing | `test_api_documents.py::test_upload_dangerous_extension_rejected` |
| Size limit | `parsing.MAX_FILE_SIZE_BYTES` (25 MB) | `test_parsing.py::test_parse_oversized_file` |
| Content-signature format detection | `parsing.detect_format` checks magic bytes, not just extension | — |
| SHA-256 hashing | Computed for every upload, stored on `DocumentVersion.sha256` | `test_api_documents.py::test_upload_computes_sha256` |
| Safe filenames / path traversal | `parsing.safe_filename` (generated id + validated extension only); storage path additionally checked with `os.path.abspath(...).startswith(...)` before write | `test_parsing.py::test_safe_filename_strips_path_traversal` |
| Parser isolation | Every parser wrapped in try/except; failures become `extraction_status=FAILED` data, never a crash | `test_parsing.py::test_parse_corrupted_json` |

## RBAC

`backend/app/core/security.ROLE_CAPABILITIES` is a deny-by-default map from
capability name to the set of roles allowed to perform it (e.g.
`CREATE_REQUIREMENT`, `RUN_PRECHECK`, `APPROVE_REVIEW`, `VIEW_AUDIT`).
`require_capability()` raises `AccessDenied` (→ HTTP 403) for anything not
explicitly listed. Tested in
`test_api_cases.py::test_citizen_cannot_create_requirement`.

## Case isolation

`assert_case_access()` is called at the top of every case- or
package-scoped route handler. An `ADMIN` may access any case; every other
role may only access a case it owns. Tested in
`test_api_cases.py::test_case_isolation_blocks_other_owner`,
`test_admin_can_access_any_case`, and
`test_api_documents.py::test_document_upload_forbidden_across_case_isolation`.

## Prompt-injection defense

See the top-level README's Safety Boundary section and
`docs/document-pipeline.md`. The key property: detection is one-way — the
scanner reads document text and may write a `Defect`; nothing reads a
`Defect` (or any document text) back into a decision about how the system
itself should behave.

## Audit

Append-only by construction — `backend/app/core/audit.record()` is the
only function in the codebase that writes an `AuditEvent`, and it always
does an `INSERT`, never an `UPDATE`. Verified in
`test_reasoning_flows.py::test_audit_trail_records_review_decision`.

## What's not yet built

- Real password-based authentication (current "session" is an
  X-User-Id header — see `backend/app/routers/users.py` and the README's
  "Current build status and limitations").
- Field-level sensitivity/redaction for exports (planned alongside the
  Section 2/3 export flow).
- Automated fuzzing/penetration test suite beyond the specific
  adversarial cases in `backend/tests/`.
