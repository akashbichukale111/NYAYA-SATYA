# Limitations — what this build does NOT do

Per the project's own "no fake functionality" principle, this file is the
single honest ledger of scope cuts. Nothing below is silently stubbed in
the running product — where the UI or API would otherwise imply a feature
exists, it either isn't exposed, or it's labeled `NOT_IMPLEMENTED` /
`SIMULATION` / `DEMO DATA` at the point of use.

## Ingestion
- OCR for images and scanned PDFs is **not implemented**. Only plain-text-like
  uploads (.txt, .md, .csv, .json) get real text extraction; everything else
  is honestly reported as `OCR_NOT_AVAILABLE`, never fabricated.
- Automatic NLP extraction of structured facts from free-form citizen
  narrative is **not implemented**. Instead, the guided intake (`POST
  /api/cases/{id}/intake`) maps each guided-form answer directly to a
  structured, source-labeled row (`USER_REPORTED`). The free-text narrative
  is stored verbatim for the record but not auto-parsed into facts.

## Conflict detection
- Only `DATE_CONFLICT` is auto-detected (same labeled timeline event
  reported with two different dates). `PARTY_CONFLICT`, `EVENT_CONFLICT`,
  `DOCUMENT_CONFLICT`, `AMOUNT_CONFLICT`, `STATUS_CONFLICT`, and
  `LOCATION_CONFLICT` are modeled as `ConflictType` enum values and
  supported everywhere downstream (packets, quality gate, UI badges) but
  have no detection rule wired up yet.

## Privacy
- The role→sensitivity-ceiling table in `privacy/engine.py` is a static,
  in-code policy. It is **not** an admin-editable rule engine
  (`PrivacyPolicy`/`AccessDecision` as persisted, configurable rows is not
  implemented — access decisions are computed on the fly, not stored).

## Handoff crash test
- Implements 5 of the 11 listed adversarial mutations: remove critical
  fact, inject unsupported fact, hide conflict, expose restricted field,
  and a role-ceiling check. Duplicate-document detection, stale
  handoff-version detection, wrong-recipient-role as a distinct persisted
  test, and a scripted regression replay of prior crash-test results are
  **not implemented**.

## Demo cases
- Seeds cases A, B, C, E, G, I (6 of the 10 listed in the master prompt).
  D (multiple handoffs), F (sensitive-field restriction as its own
  dedicated case — partially covered by Case E), H (verification failure),
  and J (incomplete narrative) are **not seeded**.

## Evaluation Lab
- No dedicated `/evaluation` API or UI screen. The crash-test battery and
  the pytest suite (`backend/tests/`) are the only measured checks in this
  build. Sections 69's full metrics list (extraction accuracy, latency
  percentiles, false-positive/negative rates, etc.) would need a labeled
  evaluation dataset this build does not include — rather than invent
  numbers, this is left **not measured**.

## Frontend
- Built as a single-page vanilla JS/HTML client (`frontend/index.html`)
  against the live API, not the React + TypeScript + Vite + Tailwind +
  Framer Motion + React Flow stack described in the master prompt. This
  was a deliberate scope trade-off to keep every screen wired to real data
  with no build step required to run the demo. The API is
  framework-agnostic, so porting screen-by-screen to React is
  straightforward and touches no backend code.
- No dedicated Case Context Graph (React Flow-style node graph), Time
  Machine scrubber (the version diff view is a simpler two-version
  comparison), low-bandwidth mode, or i18n string tables (English only;
  the backend's `preferred_language` field and plain-language copy make
  Marathi/Hindi string-table localization straightforward to add later,
  but no translated strings ship in this build).

## Security
- Authentication/authorization is **abstracted, not implemented** — there
  is no login, and role is passed by the caller (e.g. `sender_role`,
  `approved_by_role`) rather than derived from a verified session. This is
  explicitly a demo shortcut: a real deployment must bind `Role` to an
  authenticated identity before any of the privacy-ceiling logic in
  `privacy/engine.py` can be trusted.
- File upload validation is size-limited (10MB) and filename-sanitized,
  but there is no antivirus/malware scanning step.

## Multilingual / accessibility
- `Case.preferred_language` is stored but not yet used to select UI
  copy — no localization layer ships in this build.
