# Domain Model

See `backend/models.py` for the source of truth (SQLAlchemy ORM). This is
a guide to how the tables relate and why.

## Entities

- **Case** — the root aggregate. Holds the citizen's raw narrative,
  requested help, and language preference. Everything else hangs off
  `case_id`.
- **Document** — an uploaded file. Carries `extraction_method` and
  `ocr_status` so the UI never has to guess whether text was really
  extracted or not (`OCR_NOT_AVAILABLE` / `NOT_IMPLEMENTED` are valid,
  displayed values, not errors).
- **Fact** — the atomic unit of case knowledge. Always carries a
  `FactStatus` (`VERIFIED` / `DOCUMENT_SUPPORTED` / `USER_REPORTED` /
  `INFERRED` / `CONFLICTING` / `UNKNOWN` / `NOT_PROVIDED` / `SUPERSEDED`)
  and a `Sensitivity` (`PUBLIC` / `INTERNAL` / `SENSITIVE` /
  `HIGHLY_SENSITIVE`). A Fact optionally points at the Document that
  supports it (`source_document_id`) — this is the provenance link.
- **TimelineEvent** — a dated (or `NOT_PROVIDED`-dated) occurrence, tagged
  `USER_REPORTED` or `DOCUMENT_SUPPORTED`. The Conflict Engine groups
  these by a normalized label to spot date disagreements.
- **Deadline**, **Question** — self-explanatory; both carry a status/
  priority so they render consistently with Facts in the UI.
- **Conflict** — a detected contradiction. Never auto-resolved by the
  system; `resolved` only flips via explicit human action (not wired to
  an endpoint in this build — conflicts are surfaced, not resolved,
  which mirrors the "human review > autonomous decisions" principle).
- **Handoff** — one recipient/purpose pairing for a case (e.g. "Advocate
  Review" → ADVOCATE). Holds the current `HandoffState` and
  `current_version_number`.
- **HandoffVersion** — an immutable snapshot: which Fact/Document/
  TimelineEvent/Deadline/Question/Conflict IDs were included, which
  fields were excluded (with reason), the quality checklist, and the
  risk flags. Versions are **never overwritten** — a new clarification
  response creates version N+1, never mutates version N. This is what
  makes the Context Loss / diff engines meaningful.
- **Approval**, **Acknowledgement**, **Clarification** — the human
  actions taken against a specific `HandoffVersion`.
- **AgentRun** — one record per agent invocation (Context Packaging,
  Handoff Review, Context Loss), including which `LLMProvider` served it
  and the latency, so the Audit tab can show real agent activity rather
  than a black box.
- **AuditEvent** — append-only. Every state-changing endpoint writes one.

## Why versions, not mutation

The Handoff/HandoffVersion split exists specifically so
`verification/context_loss.py::compare_versions` can answer "what changed
between v1 and v2" using nothing but two foreign-key sets — no diffing of
free text, no LLM needed to describe the change.

## Known simplification

`Person`/`Party` is **not** a separate relational table in this build —
`Case.parties` is a JSON list of `{name, role}`. For a case load large
enough to need cross-case person search, promote this to a real table (see
`docs/LIMITATIONS.md`).
