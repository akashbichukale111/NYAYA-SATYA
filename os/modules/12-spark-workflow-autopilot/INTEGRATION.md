# Integration

## Upstream: 10 engine adapters

`app/adapters/adapters.py`. Each adapter's `normalize(event: dict)` takes a
plain dict (what an HTTP webhook or queue payload would look like) and
returns a `NormalizedTrigger(case_id, trigger_type, source_engine,
source_event_id, occurred_at, raw_payload)`. Adapters never read another
engine's database — they only re-shape an envelope.

| Adapter name (API path) | class | produces trigger_type |
|---|---|---|
| `case_continuity` | `CaseContinuityAdapter` | `CASE_CHANGED` |
| `evidence_dependency` | `EvidenceDependencyAdapter` | `NEW_EVIDENCE_GAP` |
| `procedural_obligation` | `ProceduralObligationAdapter` | `OBLIGATION_CREATED` / `OBLIGATION_BLOCKED` |
| `registry_defect` | `RegistryDefectAdapter` | `REGISTRY_DEFECT_DETECTED` |
| `undertrial_liberty` | `UndertrialLibertyAdapter` | `MANUAL_TRIGGER` (deliberately never automated — see below) |
| `hearing_readiness` | `HearingReadinessAdapter` | `HEARING_READINESS_BLOCKER` |
| `case_bottleneck` | `CaseBottleneckAdapter` | `CASE_BOTTLENECK_DETECTED` |
| `deadline_guardian` | `DeadlineGuardianAdapter` | `TRACKED_DATE_APPROACHING` / `PAST_TRACKED_DATE` |
| `legal_aid_handoff` | `LegalAidHandoffAdapter` | `HANDOFF_REQUIRED` |
| `crash_test` | `CrashTestAdapter` | `MANUAL_TRIGGER` |

Ingest via:

```
POST /api/adapters/{adapter_name}/ingest
{ "case_id": "...", "event_id": "...", "kind": "...", "occurred_at": "..." }
```

`event_id` becomes the idempotency key (`trigger_event_id`) — sending the
same event twice returns the existing workflow rather than creating a
duplicate (verified in `test_api_section2.py::test_adapter_ingest_is_idempotent_on_event_id`).

**Liberty-related signals are deliberately never auto-templated.**
`UndertrialLibertyAdapter` normalizes to `MANUAL_TRIGGER`, which has no
entry in `TriggerAgent.TRIGGER_TO_TEMPLATE` — ingesting one returns a
message telling the caller a human must create the workflow manually,
rather than silently picking a template for something this sensitive.

## Downstream: SPARK Personal OS

Pull-based, not push-based — SPARK Personal OS calls:

```
GET /api/cases/{case_id}/workflow-summary
```

```json
{
  "case_id": "...",
  "active_workflows": [...],
  "blocked_workflows": [...],
  "approval_required": [...],
  "tasks_due": [...],
  "verification_pending": [...],
  "attention_items": [...],
  "last_updated": "..."
}
```

`SparkPersonalOSAdapter` exists in `adapters.py` only to document this
contract in code; its `normalize()` deliberately raises `NotImplementedError`
because there is nothing to normalize inbound — the relationship is pull,
not push.

## NYAYA-SATYA position (as designed, not yet wired)

Per the long-term architecture, Workflow Autopilot sits between the
case-analysis engines and human legal judgment:

```
... hearing readiness -> SPARK WORKFLOW AUTOPILOT -> case crash test -> TARKA-VYUH -> UNWIND governance -> human legal gate
```

Nothing in this codebase has been built against a live TARKA-VYUH or UNWIND
instance — those integrations don't exist yet, and this document does not
claim otherwise. What's real today is the adapter contract above and the
pull-based summary API, which is the shape a downstream reasoning/governance
layer would consume in the same way SPARK Personal OS does.
