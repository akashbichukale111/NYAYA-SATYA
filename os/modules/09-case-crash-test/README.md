# Case Crash Test & Resilience Lab

> "Break the case safely before reality breaks it."

**Project 09** of the NYAYA-SATYA adversarial evidence & case reasoning system. This is the
cross-engine **adversarial simulation and resilience-testing layer**: given a legal case
represented as a dependency graph, it asks *"if this fact, document, obligation, deadline,
or workflow assumption changes or disappears — what breaks?"* and reports the structural
blast radius, never a legal outcome.

## Purpose

A legal case is a dependency system: evidence supports claims, claims support issues, issues
feed obligations, obligations have deadlines, deadlines feed hearing readiness. This tool lets
an analyst simulate a failure anywhere in that graph — evidence excluded, a document superseded,
a hearing result missing, a workflow action failing — and see exactly which downstream nodes
become unverified, blocked, conflicting, or in need of human review, **before** anyone relies on
the real case in that state.

## Safety boundary (read this first)

This system **never**:
- predicts a judicial outcome, conviction, acquittal, bail decision, or guilt/innocence
- invents a legal rule or a statutory deadline
- autonomously files anything, contacts authorities, or acts on the real case
- silently mutates the real case graph, or silently resolves a conflict

It only ever answers, in structural terms: what changed, what depends on it, what is affected,
what new gap/conflict/unknown/block appears, and what requires human review. See
`docs/security.md` and `backend/app/agents/agents.py`'s module docstring for how this is
enforced in code, not just in prose.

## Simulation isolation (the core invariant)

Every simulation runs against an in-memory **clone** of a snapshot (`SimGraph.clone()` in
`backend/app/graph/graph_model.py`). The real case graph in the database is never touched during
a simulation. This is asserted directly by tests, not just claimed:
- `backend/tests/test_scenarios.py`, `test_graph_engine.py` — simulation isolation on the
  in-memory graph
- `backend/app/demo/evaluation.py::_test_simulation_isolation` — a live, queryable resilience
  self-test that diffs the base graph byte-for-byte before/after a run
- `backend/tests/test_security.py` — cross-case isolation, snapshot ownership checks

The **only** endpoint allowed to write back to the live case graph is
`POST /cases/{id}/snapshots/{id}/restore`, which requires an `ADMIN` role header and a non-empty
reason (`backend/app/rbac.py`, `backend/app/simulation_engine/snapshot_service.py`).

## Architecture

```
backend/app/
  models/            SQLAlchemy domain model: Case, CaseNode, CaseRelationship, CaseSnapshot,
                      Simulation, SimulationScenario, ReviewTask, AuditEvent (see the design
                      note at the top of models/domain.py — one normalized graph, not 20+ tables)
  graph/              SimGraph (in-memory graph used during simulation) + traversal
                      (propagation, blast radius, criticality, failure trees)
  simulation_engine/  mutation_engine, diff_engine, recovery_engine, runner (orchestrates one run),
                      snapshot_service (create/restore/compare)
  agents/             Explicit named service boundaries (ScenarioPlannerAgent, MutationAgent,
                      DependencyTraversalAgent, BlastRadiusAgent, ConflictPropagationAgent,
                      VerificationImpactAgent, WorkflowImpactAgent, RecoveryPlannerAgent,
                      CounterfactualAgent, EvaluationAgent, AuditAgent) wrapping the same
                      deterministic engine — see agents.py's module docstring for why these
                      are thin wrappers, not a second implementation of the logic.
  llm/                LLMProvider interface: MockProvider (default, no API key needed),
                      OpenAIProvider, AnthropicProvider, GroqProvider. LLMs only ever produce a
                      plain-language explanation string alongside an already-computed result —
                      never the graph computation itself.
  demo/               4 deterministic DEMO cases + the Evaluation Lab (PASS/FAIL/NOT_RUN only)
  api/routes.py       All REST endpoints

frontend/src/         React + Vite + Tailwind + React Flow. Command Center, Case Graph,
                      Scenario Builder, Simulation Result, Counterfactual Lab, Time Machine,
                      Review Queue, Audit, Evaluation Lab.
```

## Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` in `backend/` if you want to use a real LLM provider for
explanations. **Nothing requires an API key** — the default `MockProvider` and DEMO mode work
with zero configuration.

## DEMO mode

`POST /api/demo/load` creates 4 deterministic synthetic cases (`backend/app/demo/demo_cases.py`):
evidence collapse, obligation cascade, registry + document failure, and a combined multi-failure
scenario. Every demo case is clearly synthetic — none of it is or represents a real case.

## API

See `backend/app/api/routes.py` for the full, current endpoint list (cases, graph, snapshots,
scenarios, simulations + diff/blast-radius/failure-tree/recovery-options, rerun, compare,
recovery-simulation, review queue + approve/reject, audit, evaluation, integration-summary).

## Testing

```bash
cd backend
python -m pytest -q
```

52 tests currently pass: graph traversal, mutation engine, simulation isolation, blast radius,
cascade/failure-tree, diff, recovery planning, scenario comparison, Time Machine restore + RBAC,
case isolation, prompt-injection inertness, and the explicit agent pipeline (parity with the
direct simulation path + full audit trace).

```bash
cd frontend
npm run build
```

## Security

RBAC (`ANALYST` / `REVIEWER` / `REVIEWER+ADMIN`) gates review approval and snapshot restore.
Case isolation is enforced and tested. Prompt-injection payloads embedded in node text are
treated as inert data by the mutation/propagation engine (tested explicitly). See
`docs/security.md` for the full threat model and what is **not yet** covered (file upload
parsing/path-traversal protection has no ingestion pipeline yet — there is nothing to protect
until Section 4 wires one up).

## Limitations (current, honest)

- RBAC reads a caller-supplied header, not a signed session — there is no login/auth provider
  wired in yet.
- No document/file upload ingestion pipeline exists yet, so upload validation and OCR/parsing
  safety are not yet applicable.
- The frontend has no automated test suite (component/e2e) — only backend tests are automated
  today.
- The per-topic files under `docs/` (architecture, domain-model, etc.) are not all written yet;
  this README plus the module docstrings in the code are the current source of truth.

## NYAYA-SATYA integration

`GET /api/cases/{case_id}/integration-summary` returns the structural/operational summary
contract (critical dependencies, fragile nodes, recent failures, affected claims/issues/
obligations/deadlines/hearings/registry-defects, blocked workflows, verification gaps, human
review items, provenance refs) described in the master prompt. It is intentionally decoupled
from any NYAYA-SATYA internals — a plain JSON contract, nothing more.
