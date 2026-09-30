# Evidence Dependency Engine

> "Know exactly which evidence supports which claim — and what breaks when that evidence disappears."

Project 06 in the NYAYA-SATYA legal-tech system. A standalone, independently-runnable
evidence reasoning and dependency-analysis engine. **It is not a judge, a lawyer, or an
outcome predictor** — it never decides guilt, innocence, liability, or a final legal
determination. It only ever says things like *"this issue currently has no verified
supporting evidence"* or *"removing this evidence affects 4 claims and 2 issues."*

## Current status (read this first)

This repository implements a **real, tested, working backend** covering both
the Section 1 foundation (domain model, dependency graph, impact analysis,
crash test, Human Legal Gate, evaluation lab, demo mode) and the Section 2
intelligence + governance layer: a real document ingestion pipeline
(PDF/DOCX/TXT/JSON/CSV, hashing, quarantine, path-traversal protection), an
`LLMProvider` abstraction, all 12 named agents with bounded authority, a
working Evidence→Claim→Issue extraction pipeline, a contradiction engine, a
verification engine, a real (not schema-only) Time Machine, and enforced
RBAC. It does **not** yet implement the full production React/TypeScript/
React-Flow frontend or the complete documentation set described in the
original brief. See **Known limitations** below and `docs/status.md` for the
precise gap list. Nothing in this repo is fabricated: every capability
described below was actually implemented and actually tested (see
"What was actually run" below).

## What's implemented and running

- **Domain model** (SQLAlchemy): Case, User, Document, EvidenceItem, Claim, Issue,
  EvidenceRelationship (generic polymorphic edge table), Conflict, ReviewTask,
  AuditEvent (append-only), EvidenceVersion + ClaimVersion (real, actively-written
  Time Machine snapshots — not schema-only), CrashTestRun.
- **Explicit uncertainty model**: `EvidenceState`, `VerificationStatus` enums (never
  silently upgraded — see `app/models/enums.py`).
- **Dependency graph engine** (`app/services/graph_service.py`): builds the
  Evidence → Claim → Issue graph (plus lateral edges) from stored rows and computes,
  from real data only:
  - coverage metrics (claims/issues with and without evidence, single-source claims,
    conflicting claims, verified/unverified counts)
  - fragility report (single-point-of-failure evidence, ranked by downstream impact)
  - missing-evidence report (unsupported claims/issues, conflicting-only support)
- **Impact analysis + Evidence Crash Test** (`app/services/impact_service.py`):
  real-time "what depends on this node" queries, and a **non-destructive** crash-test
  simulator covering all 10 event types from the spec (remove/exclude evidence, mark
  unverified, reverse relationship, introduce contradiction, supersede document,
  remove source document, invalidate provenance, break dependency, create missing
  evidence). Crash tests never mutate real case rows — verified by
  `tests/unit/test_crash_test.py`.
- **Human Legal Gate** (`app/services/review_service.py`): agents/system propose
  changes as `ReviewTask` rows; only human approval applies them; every proposal and
  decision is written to the append-only `AuditEvent` log.
- **Evaluation Lab** (`app/services/evaluation_service.py`): deterministic PASS/FAIL/
  NOT_RUN checks against real stored data (provenance completeness, claim
  traceability, issue mapping coverage, dependency consistency, case isolation,
  contradiction-detection wiring). No invented percentages.
- **NYAYA-SATYA integration adapter** (`app/api/integration.py`): a stable
  `GET /api/cases/{id}/integration-summary` contract matching the JSON shape
  specified in the brief, importing nothing from NYAYA-SATYA internals.
- **Deterministic DEMO mode**, no API key required: three fictional seeded cases —
  `A` (strong evidence chain, 3 independent documents), `B` (fragile single-point
  dependency), `C` (conflict + supersession) — seeded via
  `POST /api/cases/demo/seed/{A|B|C}`.
- **Document ingestion pipeline** (`app/services/document_service.py`): real
  upload validation (extension/MIME/size allow-lists), SHA-256 hashing, safe
  generated filenames, path-traversal-proof storage, quarantine of anything
  that fails validation, and real parsing of PDF (with real page numbers),
  DOCX, TXT, JSON, and CSV.
- **LLMProvider abstraction** (`app/core/llm_provider.py`): `MockProvider`
  (deterministic, offline, zero-key, used everywhere in this repo) plus
  structurally-real `OpenAIProvider`/`AnthropicProvider`/`GroqProvider` for
  future use.
- **12 named agents** (`app/agents/`) orchestrated by `app/agents/pipeline.py`
  into a real Document → Evidence → Claim → Issue extraction flow, triggered
  by `POST /api/documents/{id}/process`. Every extracted evidence item is a
  verbatim excerpt of the real uploaded document text — never fabricated —
  and anything consequential (issue mapping, verification) is proposed
  through the Human Legal Gate rather than applied directly. See
  `docs/agent-system.md` for the full authority table.
- **Contradiction + Verification engines**: heuristic contradiction
  detection flags conflicts for human review (never auto-resolves); the
  verification engine only proposes `VERIFIED` for claims with known-location
  support and no open contradiction, and never touches claims with no
  evidence at all.
- **Time Machine** (`app/services/time_machine_service.py`): real, append-only
  `EvidenceVersion` snapshots written on every meaningful evidence mutation;
  history, current-vs-previous diff, arbitrary version diff, and whole-case
  reconstruction at a past timestamp — all backed by real rows, nothing faked.
- **RBAC** (`app/core/rbac.py`, `app/core/case_access.py`): four roles
  (Citizen/Legal Aid/Advocate/Admin), enforced in the backend on every
  case-scoped endpoint and on the review-approval action specifically. See
  `docs/security.md` for exactly what is and isn't covered.
- **REST API** covering cases, evidence, claims, issues, relationships,
  documents, dependency graph, coverage, fragility, missing-evidence, impact,
  crash-test, review queue, audit, evaluation, time machine, and the
  integration summary.

## What was actually run (not claimed — executed)

```
$ python3 -m pytest tests/ -q
49 passed, 972 warnings in ~9.5s
```
(run repeatedly to confirm stability, not just once)

Breakdown: 9 API flow tests, 4 case-isolation tests, 7 RBAC tests, 6 agent
tests, 2 crash-test tests, 7 document-ingestion tests, 4 graph-service tests,
2 PDF-provenance tests, 8 Time Machine tests (Evidence + Claim history, diff,
current-vs-previous, and case reconstruction). Coverage includes: coverage
metrics, missing-evidence detection, single-point dependency detection,
impact traversal, crash-test non-destructiveness (byte-for-byte before/after
equality), the review-gate approve flow end-to-end, all three demo-case
seeds, case isolation, RBAC (default-admin backward compatibility, cross-user
denial, owner/admin access, demo-case openness, role-gated review approval),
document upload validation (hashing, quarantine of bad extensions/oversized/
empty files, path-traversal neutralization), the full extraction pipeline
(with an explicit anti-fabrication assertion that every created evidence item
is a substring of the real uploaded document), a real multi-page PDF fixture
proving actual page numbers are preserved (and that TXT evidence correctly
never gets a fabricated one), Time Machine history/diff/reconstruction for
both Evidence and Claim (including a regression test pinning that
demo-seeded rows get Time Machine history too, after a bug where they
initially didn't), the contradiction agent, the relationship-classification
agent, and the issue-mapping agent's propose-not-create behavior.
Prompt-injection handling is also verified: a malicious `"Ignore all
previous instructions..."` string stored as evidence text is returned
verbatim as inert data and has no effect on system behavior.

The server was also booted live (`uvicorn app.main:app`) and walked with real
HTTP calls covering both sections: seed demo case B → fragility report shows
the single ledger evidence item as `SINGLE_POINT_DEPENDENCY` → crash-test
`REMOVE_EVIDENCE` → integration summary and evaluation lab both reflect it
correctly; separately, a real `.txt` document was uploaded as an `ADVOCATE`
user (with a `CITIZEN` stranger confirmed blocked with 403), processed
through the full 12-agent pipeline, and its resulting evidence items were
confirmed verbatim-grounded in the uploaded text, source-location-unknown
(correctly, since TXT has no pagination), with a full Time Machine version 1
and a non-destructive crash test still working on agent-created evidence.

## Setup

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
uvicorn app.main:app --reload --port 8000
```

The SQLite database file is created automatically on first startup — no
migrations step is required for the demo/dev path. Visit
`http://localhost:8000/docs` for the interactive OpenAPI UI.

### Run the tests

```bash
cd /path/to/evidence-dependency-engine
python3 -m pytest tests/ -v
```

### Try DEMO mode (no API key needed)

```bash
curl -X POST http://localhost:8000/api/cases/demo/seed/A -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/api/cases/demo/seed/B -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/api/cases/demo/seed/C -H "Content-Type: application/json" -d '{}'
```
Each response includes `"is_demo": true`; the `description` field explicitly
starts with `DEMONSTRATION DATA — NOT A REAL CASE`.

## Environment variables

See `.env.example`. DEMO mode (`MockProvider`) needs zero API keys. The
`LLMProvider` abstraction (`app/core/llm_provider.py`) is fully implemented
— `MockProvider` (deterministic, offline, used everywhere by default) plus
structurally-real `OpenAIProvider`/`AnthropicProvider`/`GroqProvider` for
later use, selected via the `LLM_PROVIDER` env var.

## Security model (implemented so far)

- **Case isolation**: every query is scoped by `case_id`; verified by
  `tests/security/test_case_isolation.py` (evidence, dependency-graph, and
  case-lookup endpoints never cross case boundaries).
- **RBAC**: four roles (Citizen/Legal Aid/Advocate/Admin), enforced on every
  case-scoped backend endpoint plus the review-approval action specifically
  (role `>= ADVOCATE` required) — see `docs/security.md` for the full
  design and its honestly-documented limits (identity comes from unsigned
  headers, not real auth yet).
- **Document upload security**: extension/MIME/size allow-lists, SHA-256
  hashing of actual file bytes, safe generated filenames (never the
  user-supplied name), path-traversal-proof storage (resolved-path
  containment check), and quarantine of anything that fails validation —
  all verified by `tests/unit/test_document_ingestion.py`.
- **Untrusted-document boundary**: parsed document text and evidence
  `source_text` are stored and returned as inert string data; nothing in
  the extraction pipeline interprets it as an instruction. Verified by
  dedicated prompt-injection tests.
- **Non-destructive simulation boundary**: crash tests cannot mutate case
  data; only an approved `ReviewTask` can, and every approval is audited.
- See `docs/security.md` for the complete picture, including what's
  explicitly still a gap (real authentication, rate limiting, malware
  scanning, encryption at rest).

## Known limitations (honest gap list vs. the original brief)

- **Frontend**: not yet built. The brief calls for a full React 18 + TypeScript +
  Vite + Tailwind + Framer Motion + React Flow + TanStack Query + Zod application
  with ~17 screens. None of that exists yet in `frontend/` — building it to a
  production standard is a substantial follow-up effort in its own right.
- **RBAC is not real authentication**: roles come from `X-User-Id`/`X-User-Role`
  request headers with no signature/session verification. The enforcement
  logic (`require_role`, `require_case_access`) is real and tested, but a
  production deployment needs a real auth dependency behind it — see
  `docs/security.md`.
- **Relationship Time Machine**: Evidence and Claim both have full version
  history (creation, agent extraction, human-approved changes, demo seeding
  — all snapshot). `EvidenceRelationship` does not have its own version
  history yet.
- **Field-level sensitivity**: role-based access controls whole *cases*, not
  individual fields within one — see `docs/privacy.md`.
- **Evaluation Lab** has 6 deterministic checks covering the Section 1
  surface plus case isolation; it doesn't yet have checks specific to the
  newer agent/Time Machine/RBAC surface (see `docs/status.md`).

All eleven named docs from the original brief are written and kept in sync
with the real implementation: `docs/architecture.md`, `docs/domain-model.md`,
`docs/evidence-model.md`, `docs/security.md`, `docs/agent-system.md`,
`docs/dependency-engine.md`, `docs/privacy.md`, `docs/evaluation.md`,
`docs/api.md` (generated from the live OpenAPI schema), `docs/demo.md`, and
`docs/nyaya-satya-integration.md`.

## Exact commands to run

```bash
# Backend
cd backend
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload --port 8000

# Tests (from repo root)
python3 -m pytest tests/ -v

# Seed demo data
curl -X POST http://localhost:8000/api/cases/demo/seed/A -H "Content-Type: application/json" -d '{}'
```

## NYAYA-SATYA integration contract

`GET /api/cases/{case_id}/integration-summary` returns the exact JSON shape
specified in the master brief (`case_id`, `evidence_count`, `claim_count`,
`issue_count`, `unsupported_claims`, `unsupported_issues`, `conflicting_claims`,
`critical_dependencies`, `impact_items`, `verification_pending`,
`provenance_refs`, `attention_items`, `last_updated`). It imports nothing from
NYAYA-SATYA and can be deployed standalone.
