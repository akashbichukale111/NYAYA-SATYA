# Evaluation Lab

`GET /api/cases/{case_id}/evaluation` runs the 10 deterministic checks in
`app/core/evaluation.py::CHECKS` against a case's live data and returns
`PASS` / `FAIL` / `NOT_RUN` with a real, computed reason string per check —
never an invented percentage or score.

| Check | NOT_RUN when | FAIL when |
|---|---|---|
| `event_extraction_traceability` | No custody events exist | Any event lacks both a source document and a reporting user |
| `source_linkage` | No hearings exist | Any hearing lacks a source document |
| `timeline_consistency` | Fewer than 2 dated custody events | (structural; PASS if sortable) |
| `conflict_detection` | No differing-date events of the same type exist | Differing dates exist but no Conflict record was created |
| `dependency_correctness` | No documents ingested | Documents exist but the dependency graph has no edges |
| `historical_reconstruction` | No snapshots exist | A snapshot is missing required structural keys |
| `case_isolation` | never | A query returned a row from a different case_id |
| `prompt_injection_resistance` | No injection-style phrase present in any document | An extracted event type falls outside the fixed enum vocabulary |
| `attention_generation` | No attention items generated yet | never (informational) |
| `crash_test_correctness` | No order exists to test against | Production order count changed after a simulation, or the simulated twin didn't reflect the removal |

This last check is the one that caught the real transaction-safety bug
documented in `docs/PROJECT_STATUS.md` — it is not decorative.
