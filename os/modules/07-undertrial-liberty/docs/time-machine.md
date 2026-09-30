# Time Machine

`app/agents/time_machine.py` provides append-only, point-in-time snapshots of
the Liberty Digital Twin (`app/agents/digital_twin.py::build_digital_twin`).

## When a snapshot is taken

Automatically on: case creation, document ingestion (successful extraction),
manual custody event entry. On demand via
`POST /api/cases/{case_id}/time-machine/snapshot`.

## What a snapshot contains

The full serialized Digital Twin at that moment: `custody_state`, all current
custody events, upcoming tracked events, recent orders, bail/release events,
pending reviews, missing information, open conflicts, open attention items,
and document count. Snapshots are stored as JSON in `CaseSnapshot.snapshot_data`
and are never rewritten — only new snapshots are added.

## Diffing

`GET /api/cases/{case_id}/time-machine` returns:
- the list of all snapshots (id, reason, timestamp), and
- if `compare_a`/`compare_b` query params are given, a real structural diff
  between those two snapshots (`diff_snapshots()` in `time_machine.py`)
  computed by comparing counts and key fields (custody_state, event counts,
  missing_information, pending_review_count, etc.) — not a fabricated
  narrative.
- if no compare params are given but snapshots exist, a diff between the
  earliest snapshot and the *current live* Digital Twin, so the endpoint is
  useful with zero query parameters.

## Guarantee

Snapshots are immutable once written — there is no update or delete endpoint
for `CaseSnapshot`. This is what lets the system honestly answer "what did we
know at this point in time" without any risk of the historical record having
been quietly rewritten.
