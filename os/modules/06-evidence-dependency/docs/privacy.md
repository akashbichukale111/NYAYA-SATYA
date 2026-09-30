# Privacy

## Case isolation is the primary privacy boundary

Every query in this codebase is scoped by `case_id`. There is no endpoint
that returns data across cases (verified by
`tests/security/test_case_isolation.py` and the Evaluation Lab's
`case_isolation` check, which runs live against real data on every
`GET /api/cases/{id}/evaluation` call). Combined with RBAC
(`docs/security.md`), a case's contents are visible only to its owner,
an `ADMIN`, or -- for demo cases specifically -- anyone, since demo data
is synthetic and marked `is_demo=True`.

## What's stored, and where

- **Case data** (documents, evidence, claims, issues, relationships,
  conflicts, review tasks, audit events, version history) lives in the
  SQLite database file (`evidence_dependency_engine.db` by default) and,
  for uploaded documents, on disk under `UPLOAD_DIR` (validated files) or
  `QUARANTINE_DIR` (rejected files).
- **Identity**: this pass has no real authentication (see
  `docs/security.md`'s Known limitations) -- `User` rows and
  `Case.owner_user_id` are populated from client-supplied `X-User-Id`
  headers, not verified credentials. A production deployment must add
  real auth before this becomes a genuine privacy boundary rather than an
  honor-system one.
- **Nothing is sent to a third party by default.** `LLM_PROVIDER` defaults
  to `mock` (`app/core/llm_provider.py`), which never makes a network
  call. Document text and evidence/claim content only leave this
  deployment if an operator explicitly configures `LLM_PROVIDER=openai`
  (or anthropic/groq) and supplies an API key -- at which point document
  excerpts would be sent to that provider for extraction. This is
  documented, not hidden, and is off by default.

## Field sensitivity

The domain model doesn't currently have a generic "sensitive field" flag
distinct from case-level access control -- every field on an
`EvidenceItem`/`Claim`/`Issue` is visible to anyone with access to the
case. The brief's "field sensitivity" requirement is only partially
addressed: role-based access controls *cases*, not individual fields
within a case. A finer-grained scheme (e.g. redacting `source_text` for
`CITIZEN`-role viewers) is not implemented and is a documented gap.

## Audit trail as a privacy control

Every read is not logged (that would be excessive for a read-heavy API),
but every **write** -- case creation, evidence/claim/issue creation,
relationship creation, document upload, agent actions, review
approvals/rejections -- is written to the append-only `AuditEvent` log
with the actor's user ID (or agent name) attached. This gives a case
owner or admin a complete, tamper-evident (append-only, never
updated/deleted) record of who touched what and when.

## Untrusted document content

Uploaded document text is never treated as anything other than data --
see `docs/security.md`'s prompt-injection section. This matters for
privacy too: a document's content cannot cause the system to exfiltrate
other cases' data or change access rules, because content is never
interpreted as a query, a permission, or an instruction anywhere in the
pipeline.

## What this pass does not implement

- Field-level redaction / sensitivity labels
- Data retention / deletion policies (a case, once created, persists
  indefinitely in this pass -- there's no "right to be forgotten" flow)
- Encryption at rest
- PII detection or automatic redaction in extracted evidence text
- A consent flow for enabling a paid LLM provider (it's an environment
  variable an operator sets; there's no in-app toggle or user-facing
  disclosure screen yet, since there's no frontend yet)

These are honest gaps, not oversights being glossed over -- see
`docs/status.md` for where they sit in the priority list for follow-up work.
