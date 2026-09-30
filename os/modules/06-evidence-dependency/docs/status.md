# Build status vs. the Project 06 master brief

This file exists so a future session (or another engineer) can pick up exactly
where this one left off, without re-deriving what's done.

## Done, tested, and verified working (Section 1 + Section 2)

### Domain + core engine (Section 1)
- [x] Repo structure (backend/frontend/demo/docs/tests/scripts)
- [x] Domain model: Case, User, Document, EvidenceItem, Claim, Issue,
      EvidenceRelationship, Conflict, ReviewTask, AuditEvent, EvidenceVersion,
      CrashTestRun (SQLAlchemy, SQLite now / Postgres-ready)
- [x] Evidence state + verification enums with explicit uncertainty states
- [x] Dependency graph builder + traversal (BFS, forward/backward adjacency)
- [x] Coverage metrics, fragility/single-point-dependency detection,
      missing-evidence detection -- all real, graph-derived, no invented numbers
- [x] Impact analysis (real-time downstream query)
- [x] Evidence Crash Test (10 event types, non-destructive, proven by test)
- [x] Human Legal Gate (propose → review queue → approve/reject → apply → audit)
- [x] Append-only audit log
- [x] Evaluation Lab (deterministic PASS/FAIL/NOT_RUN checks, no invented metrics)
- [x] 3 deterministic demo cases (A strong chain / B fragile / C conflict)
- [x] NYAYA-SATYA integration summary endpoint matching the spec'd JSON shape

### Intelligence + governance layer (Section 2, this pass)
- [x] **Document ingestion pipeline**: upload endpoint, extension/MIME/size
      validation, SHA-256 hashing, safe on-disk filenames, path-traversal
      protection (resolved-path containment check), quarantine on validation
      failure, PDF/DOCX/TXT/JSON/CSV parsing (real page numbers preserved
      for PDF; source_location_known=False for formats without reliable
      pagination), parse-error handling that never crashes the request.
      `app/services/document_service.py` + `app/api/documents.py`.
- [x] **LLMProvider abstraction**: `LLMProvider` (abstract), `MockProvider`
      (deterministic, offline, zero-key, anti-fabrication contract enforced
      at runtime), `OpenAIProvider`/`AnthropicProvider`/`GroqProvider`
      (structurally real client code, never exercised by tests here).
      `app/core/llm_provider.py`.
- [x] **12 named agents** with real, bounded authority (additive-only /
      read-only / gated-behind-Human-Legal-Gate -- see `docs/agent-system.md`
      for the authority table) + a `pipeline.py` orchestrator wired to
      `POST /api/documents/{id}/process`.
- [x] **Evidence → Claim → Issue pipeline**: real document text in, real
      verbatim-grounded EvidenceItem/Claim rows out; anti-fabrication
      asserted in code and verified by test.
- [x] **Contradiction engine**: heuristic negation/vocabulary check flags a
      `Conflict` + `CONTRADICTS` edge, always `REQUIRES_HUMAN_REVIEW`, never
      auto-resolves.
- [x] **Verification engine**: `VerificationAgent` only proposes `VERIFIED`
      for claims with known-location support and no open contradiction;
      claims with no evidence are never touched -- missing evidence
      provably blocks verification (tested).
- [x] **Temporal state / Time Machine**: `EvidenceVersion` now actually
      written on every meaningful evidence mutation (creation, agent
      extraction, human-approved change) via `time_machine_service.py`;
      real history, current-vs-previous diff, arbitrary-version diff, and
      whole-case reconstruction at a past timestamp, all backed by real
      snapshot rows -- nothing faked.
- [x] **RBAC**: `Actor`/`get_actor`/`require_role`/`require_case_access` in
      `app/core/rbac.py` + `app/core/case_access.py`, enforced on every
      case-scoped endpoint (not just the frontend, which doesn't exist yet
      anyway) and on the review-approval action specifically (role
      `>= ADVOCATE` required).
- [x] **Case isolation**: re-verified under the new endpoints too.
- [x] **Prompt-injection defense**: re-verified; document text flows through
      the whole extraction pipeline as inert data.
- [x] **Audit**: unchanged append-only design, now also receiving agent
      actions (`actor_type=AGENT`) alongside user/system actions.
- [x] docs/security.md and docs/agent-system.md written to match the real
      implementation (not aspirational).

## Test suite (49 tests, all passing, run repeatedly to confirm stability)
```
tests/api/test_api_flows.py .......... 9
tests/security/test_case_isolation.py . 4
tests/security/test_rbac.py ........... 7
tests/unit/test_agents.py ............. 6
tests/unit/test_crash_test.py ......... 2
tests/unit/test_document_ingestion.py . 7
tests/unit/test_graph_service.py ...... 4
tests/unit/test_pdf_provenance.py ..... 2
tests/unit/test_time_machine.py ....... 8
```
The original 19 Section-1 tests are unmodified and still pass unchanged.

## Closed since the last status update
- Time Machine now covers Claims as well as Evidence (`ClaimVersion` table,
  full history/diff/current-vs-previous/reconstruction parity with the
  Evidence side) -- including a fix so demo-seeded evidence and claims get
  Time Machine history too (they didn't initially; caught live during a
  post-implementation sanity check and pinned with
  `test_demo_seeded_evidence_and_claims_have_time_machine_history`).
- A real multi-page PDF test fixture (`tests/fixtures/sample_multipage.pdf`)
  now exists and `tests/unit/test_pdf_provenance.py` proves real PyPDF2 page
  numbers are preserved end-to-end through upload → pipeline → evidence
  rows (and, by contrast, that TXT evidence correctly never gets a
  fabricated page number).
- All eleven named docs from the original brief are now written:
  architecture.md, domain-model.md, evidence-model.md, security.md,
  agent-system.md, dependency-engine.md, privacy.md, evaluation.md, api.md
  (generated from the live OpenAPI schema, not hand-typed), demo.md,
  nyaya-satya-integration.md.

## Not yet built (next session should start here, in this order)
1. **Frontend**: still nothing built. Highest-value next step given how
   much real backend surface now exists to wire up.
2. **RBAC → real auth**: swap header-based `get_actor` for a JWT/session
   dependency; the enforcement points (`require_role`, `require_case_access`)
   don't need to change.
3. **Evaluation Lab expansion**: add checks for the newer surface (e.g.
   "every AGENT-actor audit event has a corresponding ReviewTask when its
   action_type is gated", "every EvidenceItem/Claim has Time Machine
   history with no gaps").
4. **Field-level sensitivity**: role currently gates whole cases, not
   individual fields within one (documented in docs/privacy.md).
5. **Relationship Time Machine**: EvidenceItem and Claim both have full
   version history now; EvidenceRelationship does not yet.

## Design decisions worth knowing about before extending this
- `EvidenceRelationship` is one generic polymorphic edge table
  (`source_type`/`source_id`/`target_type`/`target_id`) rather than N join
  tables, so Evidence↔Evidence, Claim↔Claim, Evidence↔Claim, Claim↔Issue,
  Evidence↔Issue, Issue↔Issue edges all live in one place. `graph_service.py`
  builds an in-memory adjacency from these rows per request; this is fine at
  demo scale and should be revisited if case graphs get large (thousands of
  nodes) -- add caching or move traversal into SQL recursive CTEs then.
- "Independent source" for redundancy/single-point detection is currently
  computed by distinct upstream `document_id`, not distinct evidence rows --
  this directly implements the brief's instruction not to assume independence
  just because two evidence items are different files. The Relationship
  Agent (Section 2) uses the same rule to decide SUPPORTS→CORROBORATES
  upgrades.
- Crash tests are pure read + simulate + persist-a-CrashTestRun-row; they
  never touch `EvidenceItem`/`Claim`/`Issue`/`EvidenceRelationship`. Real
  destructive/consequential changes only ever happen inside
  `review_service._apply_change`, which only runs after
  `decide(..., approve=True)`. Section 2 extended `_apply_change` to also
  handle `RELATIONSHIP_PROPOSAL` (materializing an agent-proposed edge) and
  `CONFLICT` (resolving a flagged contradiction) targets, and it now writes
  an `EvidenceVersion` snapshot whenever it mutates an `EvidenceItem`.
- Agent authority is intentionally asymmetric: creating brand-new,
  `UNVERIFIED`/`REQUIRES_HUMAN_REVIEW` data is additive and safe to do
  directly (nothing existing is touched); *changing* or *relying on*
  existing verified data always goes through the Human Legal Gate. This is
  the rule to follow when adding a 13th agent.
- RBAC's "no headers = ADMIN/system-user" default exists purely for
  backward compatibility with the Section 1 test suite and any direct API
  caller during local development. It is explicitly called out as a
  pre-production gap in docs/security.md -- don't remove the tests that
  pin this behavior without also fixing the default.
