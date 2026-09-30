# Architecture

## Layout

```
evidence-dependency-engine/
├── backend/
│   └── app/
│       ├── main.py            FastAPI app, router registration, CORS, startup
│       ├── core/               cross-cutting: db session, RBAC, case access, LLM provider
│       ├── models/             SQLAlchemy ORM (orm.py) + domain enums (enums.py)
│       ├── schemas/             Pydantic request/response models
│       ├── services/            business logic (graph, impact, review/gate, evaluation,
│       │                        document ingestion, time machine)
│       ├── agents/               12 named agent modules + pipeline.py orchestrator
│       ├── api/                  one router module per resource, thin (validation +
│       │                        delegation to services/agents, no business logic)
│       └── demo_data/           deterministic offline demo case seeders
├── tests/
│   ├── unit/                    service- and agent-level tests
│   ├── api/                     end-to-end HTTP flow tests
│   ├── security/                RBAC, case isolation, prompt injection
│   └── fixtures/                real binary fixtures (e.g. a generated multi-page PDF)
├── frontend/                    not yet built (see docs/status.md)
└── docs/                        this documentation set
```

## Layering rule

`api/` → `agents/` and/or `services/` → `models/`. API routers never touch
the ORM directly except for simple, single-table reads/writes that don't
involve graph logic (e.g. `GET /api/cases/{id}` just queries `Case`).
Anything touching the dependency graph, impact analysis, crash tests, the
review gate, or agent behavior goes through `services/` or `agents/`, never
inline in a router function. This keeps the graph/impact logic testable
without spinning up HTTP at all (see `tests/unit/test_graph_service.py`,
which calls the API layer for setup but could equally call the service
functions directly).

## Request flow example: crash test

```
POST /api/evidence/{id}/crash-test
  → app/api/crash_test.py: validates evidence exists, checks RBAC/case access
  → app/services/impact_service.run_crash_test()
      → app/services/graph_service.DependencyGraph(db, case_id)
          builds in-memory adjacency from EvidenceRelationship rows
      → computes affected claims/issues via BFS over SUPPORT_LIKE edges
      → persists a CrashTestRun row (before_state/after_state/affected_*)
      → NEVER writes to EvidenceItem/Claim/Issue/EvidenceRelationship
  → response includes "SIMULATION ONLY -- no case data was modified."
```

## Request flow example: document → evidence → claim pipeline

```
POST /api/cases/{case_id}/documents (multipart upload)
  → app/services/document_service.validate_and_store()
      validates extension/MIME/size, hashes, writes to case-scoped dir
      or quarantines; creates a Document row
POST /api/documents/{id}/process
  → app/agents/pipeline.run_pipeline()
      1. evidence_intake_agent.check_intake()        -- read-only check
      2. evidence_extraction_agent.extract_evidence() -- parses + creates
         verbatim EvidenceItem rows (REQUIRES_HUMAN_REVIEW)
      3. claim_discovery_agent.discover_claims()      -- one Claim per
         evidence item, text = evidence's own text
      4. issue_mapping_agent.propose_mappings()       -- GATED: creates
         ReviewTask, not a live relationship
      5. relationship_agent.classify_support()        -- upgrades SUPPORTS
         to CORROBORATES where independently sourced
      6. contradiction_agent.detect_contradictions()  -- flags Conflict rows
      7. verification_agent.recommend_verifications() -- GATED: proposes
         VERIFIED via ReviewTask
      8. dependency_agent.report()                    -- coverage snapshot
  → every step's output is returned in the API response AND audited
```

## Database

SQLite for local/demo use (`DATABASE_URL` env var, default
`sqlite:///./evidence_dependency_engine.db`). The ORM (`app/models/orm.py`)
uses only portable SQLAlchemy types (`String`, `DateTime`, `Integer`,
`Boolean`, `JSON`, `Text`) with no SQLite-specific features, so switching
`DATABASE_URL` to a PostgreSQL DSN requires no model changes -- see
`docker-compose.yml` for where that variable is set. `EvidenceRelationship`
is deliberately one generic polymorphic table (see docs/dependency-engine.md)
rather than per-pair join tables, which keeps the graph traversal code in
one place regardless of which node types are connected.

## Why services return real data structures, not opinions

Every function in `app/services/graph_service.py`,
`app/services/impact_service.py`, and `app/services/evaluation_service.py`
returns numbers and lists computed directly from queried rows -- there is
no code path in this repository that invents a percentage, a confidence
score, or a metric that isn't a direct count/traversal result. This is a
deliberate architectural constraint (see the "PASS/FAIL/NOT_RUN, never an
invented score" rule in docs/evaluation.md) and is why the Evaluation Lab
can meaningfully check `dependency_consistency`, `case_isolation`, etc.
against the running system rather than against a fixture.
