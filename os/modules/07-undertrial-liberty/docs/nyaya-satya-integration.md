# NYAYA-SATYA Integration

## Position in the integration chain

```
Legal-Aid Handoff
        ↓
Case Continuity
        ↓
Procedural Obligation
        ↓
Evidence Dependency
        ↓
Undertrial Liberty Sentinel   <-- this module
        ↓
Case Bottleneck
        ↓
Hearing Readiness
        ↓
TARKA-VYUH
        ↓
UNWIND Governance & Audit Core
        ↓
Human Legal Gate
```

## Contract

`GET /api/cases/{case_id}/integration/nyaya-satya` (implemented in
`app/api/analysis.py::get_integration_adapter`) returns:

```json
{
  "case_id": "...",
  "custody_state": "...",
  "custody_state_confidence": "...",
  "latest_verified_event": {...} | null,
  "upcoming_tracked_events": [...],
  "attention_items": [...],
  "conflicts": [...],
  "missing_information": [...],
  "verification_pending": [...],
  "dependency_items": [...],
  "provenance_refs": [...],
  "last_updated": "...",
  "disclaimer": "This is an operational tracking summary. It is not a legal conclusion, bail determination, or custody-lawfulness assessment."
}
```

This matches the shape in the master spec exactly, plus an explicit
`disclaimer` field so any downstream consumer receives the safety boundary
inline with the data, not just in documentation.

## Independence

This module is fully self-contained: it can be run, seeded (DEMO mode), and
queried with no other NYAYA-SATYA component present. Downstream modules
(Case Bottleneck, Hearing Readiness, TARKA-VYUH, etc.) are expected to poll or
subscribe to this endpoint rather than reach into this module's database
directly, preserving the module boundary.

## What downstream consumers must not do with this data

Per the master spec's safety boundary, no downstream module may treat
`custody_state` or any attention item as a legal conclusion, a bail
prediction, or grounds for automatic action (e.g. auto-filing a release
request). The `disclaimer` field exists specifically to make this
unambiguous at the integration boundary.
