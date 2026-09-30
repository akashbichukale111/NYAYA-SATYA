# Demo Mode

Run `python -m app.db.seed_demo` from `backend/` against a fresh database.
It requires no external API key and creates exactly three cases, each
labeled `is_demo=true` (rendered in the UI as
`DEMONSTRATION DATA — NOT A REAL CASE`).

## Demo A — Clean Timeline

Five synthetic documents (arrest memo, remand order, bail application, bail
order, release document) ingest into a fully-linked custody → hearing →
order → release chain. `custody_state` resolves to
`CUSTODY_STATE_KNOWN_VERIFIED`.

## Demo B — Conflicting Records

A station record and a prison intake record disagree on the arrest date
(12 vs 14 February 2026). The reconciliation agent detects this, opens a
`Conflict`, and a `ReviewTask` is created requiring human resolution —
`custody_state` resolves to `CUSTODY_STATE_CONFLICTING`.

## Demo C — Missing Event Chain

An arrest/remand document and a hearing notice are ingested, but no order
document is ever provided for that hearing. Once the attention engine is run
against a reference date after the hearing date, `PAST_TRACKED_DATE` and
`MISSING_HEARING_RESULT` attention items are generated.

## Suggested walkthrough

Open Demo B → Custody Timeline (see both conflicting dates with their
source snippets) → Conflicts tab (see the open conflict) → Attention Center
(see the `REQUIRES_HUMAN_REVIEW` item) → Review Queue (see the pending task)
→ Time Machine (see the initial snapshot) → Evaluation Lab (see
`conflict_detection: PASS`).
