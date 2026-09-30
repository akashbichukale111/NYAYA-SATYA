# NYAYA-SATYA Integration Contract

This project owns **CONTEXT TRANSFER** — carrying case context across a
human handoff without loss, distortion, or over-exposure. It does not own
case state (Case Continuity Engine), flow blockers (Case Bottleneck
Engine), or hearing readiness (Hearing Readiness Engine). Those systems
are expected to sit alongside this one; this document describes the
contract at their boundary.

## Input this system expects

From a Case Continuity / Case Digital Twin system (or, standalone, from
citizen intake directly):

```json
{
  "case_id": "string",
  "citizen_narrative": "string",
  "facts": [{"label": "string", "statement": "string", "status": "FactStatus", "sensitivity": "Sensitivity"}],
  "documents": [{"filename": "string", "extracted_text": "string|null"}],
  "timeline_events": [{"event_date": "ISO date|null", "description": "string", "source_type": "string"}],
  "deadlines": [{"description": "string", "due_date": "ISO date|null"}]
}
```

In this standalone build, that shape is produced by the guided intake
endpoint (`POST /api/cases/{id}/intake`) and document upload endpoint
(`POST /api/cases/{id}/documents`) rather than received from an external
Case Continuity system — there is no live NYAYA-SATYA integration wired up
in this build (tracked in `docs/LIMITATIONS.md`).

## Output this system produces

Everything under `/api/cases/{id}/...` is available for a downstream
system to consume:

| Output | Endpoint |
|---|---|
| Structured facts + status | `GET /api/cases/{id}/facts` |
| Timeline | `GET /api/cases/{id}/timeline` |
| Missing information | `GET /api/cases/{id}/missing-information` |
| Conflicts | `GET /api/cases/{id}/conflicts` |
| Handoff packets + versions | `GET /api/cases/{id}/handoffs/{handoff_id}` |
| Acknowledgement / clarification history | embedded in the handoff-version response (`acknowledged`, and via `GET /api/cases/{id}/audit`) |
| Provenance | `Fact.source_document_id` / `Fact.provenance_id` on every fact row |
| Audit records | `GET /api/cases/{id}/audit` |

## Future pipeline

```
CITIZEN
  ↓
LEGAL-AID HANDOFF   (this project)
  ↓
CASE CONTINUITY
  ↓
BOTTLENECK
  ↓
HEARING READINESS
  ↓
TARKA-VYUH
  ↓
UNWIND
```

Each arrow is a contract boundary, not a shared database. A downstream
system should treat this project's API as its only interface into
handoff/context-transfer state — it should not reach into this project's
SQLite/Postgres tables directly, since `HandoffVersion` snapshots and the
privacy-ceiling logic in `privacy/engine.py` are invariants this API
enforces on every read.
