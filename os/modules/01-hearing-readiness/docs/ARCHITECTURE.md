# Architecture

## Layers (mapped to the build brief's section 2 list)

| Brief's layer | Implementation | Status |
|---|---|---|
| A. Presentation | `frontend/` React+TS+Vite+Tailwind SPA | Implemented |
| B. API | `backend/app/api/*` FastAPI routers | Implemented |
| C. Case Digital Twin | `backend/app/services/case_twin.py` + domain models | Implemented |
| D. Document/Evidence Intelligence | `backend/app/services/ingestion.py` | Implemented (txt/json/csv/docx/pdf-text; no OCR) |
| E. Hearing Context Engine | `backend/app/services/hearing_context.py` | Implemented (rule/keyword-based) |
| F. Readiness Audit Engine | `backend/app/services/readiness_engine.py` | Implemented, pure + deterministic |
| G. Blocker Intelligence Engine | `backend/app/services/blocker_engine.py` | Implemented |
| H. Causal Dependency Graph | `backend/app/services/causal_graph.py` + `frontend/.../CausalGraph.tsx` | Implemented |
| I. Agentic Action Planner | `backend/app/agents/*` + `orchestrator.py` | Implemented |
| J. Human Approval Gate | `backend/app/api/routes_ops.py` (`/actions/{id}/approve`) + `tools/registry.py` enforcement | Implemented |
| K. Action Verification Engine | `backend/app/services/verification_engine.py` | Implemented |
| L. Readiness Simulation Engine | `backend/app/services/simulation_engine.py` | Implemented, non-destructive |
| M. Readiness Time Machine | `backend/app/services/time_machine.py` | Implemented |
| N. Crash Test Engine | `backend/app/services/crash_test_engine.py` | Implemented, 9 mutation types |
| O. Provenance/Audit | `backend/app/services/audit_service.py` + provenance fields on models | Implemented |
| P. Security/Authority Firewall | `backend/app/services/security.py` | Implemented |
| Q. Evaluation Lab | `backend/app/api/routes_eval.py` | Implemented (real metrics; several honestly marked NOT_YET_MEASURED) |
| R. Observability | Structured `AgentRun`/`AuditEvent` traces | Partial — no latency/timing instrumentation (see Evaluation Lab) |

## Why services are separated from agents

Every piece of actual logic (readiness math, blocker rules, causal graph
sync, verification checks, simulation, crash-test mutations) lives in
`backend/app/services/*` as plain, mostly-pure functions that take and
return dicts/ORM rows. `backend/app/agents/*` is a thin orchestration
layer: each agent is a single-responsibility wrapper that calls one or two
service functions and returns a `StepResult`. This split exists so:

1. **Testability.** `services/readiness_engine.py`'s core functions are
   pure — no DB, no I/O — so they're covered by fast, deterministic unit
   tests (`tests/test_readiness_engine.py`) independent of any agent
   framework.
2. **No duplicated state.** Agents never keep their own copy of case
   state; they read/write through `case_twin.py`, exactly as section 3
   of the brief requires.
3. **The LLM is optional and narrow.** `services/llm_provider.py` is only
   ever asked to phrase narrative text (and only in a couple of
   currently-unused hook points) — it is never in the path of computing
   readiness, blockers, or verification. Swapping providers, or running
   with none at all (`DEMO_MODE`), cannot change what the system decides.

## Data flow for one demo pass

```
POST /cases/{id}/run-agent-pass
  -> IntakeAgent            (reads case_twin.get_case_full)
  -> CaseStateAgent          (reads case_twin.get_case_full)
  -> HearingContextAgent     (case_twin.refresh_hearing_context -> hearing_context.determine_purpose)
  -> ReadinessAgent          (readiness_engine.run_readiness_audit)
       - recomputes every Requirement.status from linked Evidence
       - blocker_engine.sync_blockers (create/update/resolve Blocker rows)
       - causal_graph.sync_dependencies (rebuild Dependency rows)
       - time_machine.snapshot_version (immutable CaseVersion row)
       - audit_service.log_event
  -> BlockerInvestigationAgent (explanation_engine.explain_blocker per open blocker)
  -> EvidenceVerificationAgent (flags UNVERIFIED/DISPUTED evidence)
  -> ActionPlanningAgent      (action_planner.propose_action per open blocker
                                without an existing action -> Action row,
                                status=PENDING_APPROVAL)
  -> AuditAgent               (logs the whole pass)
```

Nothing above changes case-visible state without a subsequent human
decision. The next step only happens via:

```
POST /cases/{id}/actions/{action_id}/approve  {decision: "APPROVE"}
  -> Approval row created
  -> run_post_approval_pass()
       -> VerificationAgent
            - refuses if no Approval with decision=APPROVE exists
            - verification_engine.execute_action (produces artifact)
            - verification_engine.verify_action (re-reads DB fresh, checks artifact)
       -> ReadinessAgent (re-run, so state reflects the verified action)
       -> AuditAgent
```

## Known limitations (see README for the full honesty table)

- No OCR: scanned/image-only PDFs are reported as `OCR_NOT_AVAILABLE`,
  not silently skipped or guessed.
- No authentication/multi-tenancy (single implicit demo user).
- No labeled ground-truth dataset, so extraction accuracy and
  false-positive/negative blocker rates are not measurable yet
  (Evaluation Lab reports this honestly rather than inventing numbers).
- LLM narrative-generation hooks exist in `llm_provider.py` but are not
  yet called from the readiness/blocker path, by design — that path must
  stay deterministic and explainable.
