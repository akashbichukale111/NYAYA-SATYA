# Demo mode

Zero API keys, zero network calls, fully deterministic. `LLM_PROVIDER`
defaults to `mock` (see `app/core/llm_provider.py`), and the three seeded
demo cases are built from fixed Python code
(`app/demo_data/seed.py`), not an LLM call -- running the seed twice
produces structurally identical (if differently-UUID'd) data every time.

Every demo case is created with `is_demo=True`, which does two things:
it bypasses RBAC ownership checks (anyone can view it -- see
`docs/security.md`), and its `description` field explicitly opens with
**"DEMONSTRATION DATA — NOT A REAL CASE."**

## Seeding

```bash
curl -X POST http://localhost:8000/api/cases/demo/seed/A -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/api/cases/demo/seed/B -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/api/cases/demo/seed/C -H "Content-Type: application/json" -d '{}'
```

Each call creates a fresh case (calling the same seed twice gives you two
separate demo cases, not an update to one).

## Demo Case A — Strong Evidence Chain

Three documents (a delivery receipt, a courier GPS log, a witness
statement) each provide one evidence item supporting a single claim
("goods delivered on 12 March"), which in turn supports one issue. Because
all three evidence items come from **different** `document_id`s, they
count as independently corroborating (see docs/dependency-engine.md's
"Independence, not just difference"). Hitting
`GET /cases/{id}/coverage` shows `single_source_claims: 0` for this case
-- verified by `tests/api/test_api_flows.py::test_demo_seed_a_produces_strong_chain`.

## Demo Case B — Fragile Dependency

One unverified ledger page (`document_id` shared by nothing else in the
case) is the *sole* support for two separate claims, which in turn support
two separate issues. `GET /cases/{id}/fragility` shows this evidence item
as `SINGLE_POINT_DEPENDENCY` with both claims and both issues in its
downstream impact -- verified by
`test_demo_seed_b_produces_single_point_dependency`. This is the case to
use for demonstrating the Evidence Crash Test: running `REMOVE_EVIDENCE`
on this one evidence item shows exactly what the product is for.

## Demo Case C — Conflict + Supersession

An original order, an amended order that `SUPERSEDES` it, and a
conflicting affidavit that `CONTRADICTS` the claim the amended order
supports. `GET /cases/{id}/coverage` shows `conflicting_claims: 1` --
verified by `test_demo_seed_c_produces_conflict`.

## Suggested flagship walkthrough (all real, all scriptable)

```
1. POST /cases/demo/seed/B                          -> get case_id
2. GET  /cases/{id}/fragility                        -> see the SINGLE_POINT_DEPENDENCY
3. GET  /cases/{id}/evidence                         -> get the fragile evidence_id
4. POST /evidence/{evidence_id}/crash-test            -> {"event_type":"REMOVE_EVIDENCE",...}
                                                          -> see affected_claims/issues, new_gaps,
                                                             human_review_required:true, and the
                                                             "SIMULATION ONLY" note
5. GET  /cases/{id}/integration-summary               -> same evidence item listed under
                                                          critical_dependencies
6. GET  /cases/{id}/evaluation                        -> PASS/FAIL/NOT_RUN, no invented metrics
```

This exact sequence was run live against a booted server as part of
verifying this build -- see the "What was actually run" section of the
top-level README.

## Uploading and processing a real document in DEMO mode

Because `LLM_PROVIDER=mock` requires no key, the full document ingestion
+ 12-agent extraction pipeline also works with zero configuration:

```bash
curl -X POST http://localhost:8000/api/cases/{case_id}/documents \
  -F "file=@my_document.txt;type=text/plain"
curl -X POST http://localhost:8000/api/documents/{document_id}/process
```

Every evidence item this produces is a verbatim excerpt of the uploaded
text -- see `docs/agent-system.md`'s anti-fabrication contract.
