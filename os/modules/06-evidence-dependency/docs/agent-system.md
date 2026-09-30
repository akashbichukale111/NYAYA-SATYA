# Agent system

Twelve named agent boundaries, each a real Python module under
`backend/app/agents/`, orchestrated in sequence by
`backend/app/agents/pipeline.py::run_pipeline()`, triggered by
`POST /api/documents/{document_id}/process`.

## The authority rule

Every agent below is either:
- **read-only / reporting** (Dependency, Provenance, Impact, Audit query,
  Crash-Test-as-simulation) -- no authority needed, nothing consequential
  happens; or
- **additive-only** (Evidence Intake, Evidence Extraction, Claim Discovery,
  Relationship reclassification) -- creates new `UNVERIFIED` /
  `REQUIRES_HUMAN_REVIEW` rows, or flags a conflict, without modifying or
  hiding anything that already existed; or
- **gated** (Issue Mapping, Verification) -- proposes a change via
  `review_service.propose_action` / `propose_relationship` and has *no*
  code path that applies the change itself. Only `review_service.decide()`,
  called from `POST /api/reviews/{id}/approve` by a human with role
  `>= ADVOCATE`, can make the change real.

No agent can exclude evidence, change a verification status to `VERIFIED`,
resolve a conflict, or create a Claim->Issue mapping without a human
approval in between.

## The twelve agents

| # | Agent | File | Authority |
|---|-------|------|-----------|
| 1 | Evidence Intake | `evidence_intake_agent.py` | read-only status check |
| 2 | Evidence Extraction | `evidence_extraction_agent.py` | additive (creates UNVERIFIED evidence) |
| 3 | Claim Discovery | `claim_discovery_agent.py` | additive (creates UNVERIFIED claims, grounded verbatim in evidence text) |
| 4 | Issue Mapping | `issue_mapping_agent.py` | **gated** -- proposes Claim→Issue edge only |
| 5 | Relationship | `relationship_agent.py` | additive (reclassifies existing SUPPORTS→CORROBORATES, creates nothing new) |
| 6 | Contradiction | `contradiction_agent.py` | additive (flags a Conflict + CONTRADICTS edge; never resolves) |
| 7 | Dependency | `dependency_agent.py` | read-only (wraps `graph_service`) |
| 8 | Provenance | `provenance_agent.py` | read-only (source-location completeness report) |
| 9 | Verification | `verification_agent.py` | **gated** -- proposes VERIFIED status only |
| 10 | Impact | `impact_agent.py` | read-only (wraps `impact_service.compute_impact`) |
| 11 | Crash-Test | `crash_test_agent.py` | simulation-only (wraps `impact_service.run_crash_test`, non-destructive) |
| 12 | Audit | `audit_agent.py` | append-only write + read query over `AuditEvent` |

## Anti-fabrication contract

`app/core/llm_provider.py::MockProvider.extract_evidence_candidates` only
ever returns strings that are verbatim substrings of the input text (the
implementation asserts this at runtime). `EvidenceExtractionAgent`
double-checks the substring property again before creating each
`EvidenceItem`. `ClaimDiscoveryAgent` sets a claim's text to the
originating evidence's own text -- it does not paraphrase or infer new
content. This is exercised end-to-end by
`tests/unit/test_document_ingestion.py::test_document_process_pipeline_creates_grounded_evidence_and_claims`,
which asserts every evidence item created by a real pipeline run is a
substring of the actual uploaded document content.

## Pipeline order (`run_pipeline`)

```
Evidence Intake (validate document is ingested)
  → Evidence Extraction (parse + extract verbatim candidates)
  → Claim Discovery (one claim per extracted evidence item)
  → Issue Mapping (propose Claim→Issue edges, gated)
  → Relationship (reclassify SUPPORTS→CORROBORATES where independent)
  → Contradiction (flag conflicts between evidence on the same claim)
  → Verification (propose VERIFIED for well-supported, uncontested claims, gated)
  → Dependency report (coverage snapshot after the run)
```

Every step's output is both returned in the API response and written to
the audit log (`actor` set to the agent's own name, `actor_type=AGENT`).

## LLM provider abstraction

`app/core/llm_provider.py` defines `LLMProvider` (abstract),
`MockProvider` (deterministic, offline, used by DEMO mode and every
automated test), and structurally-real `OpenAIProvider`,
`AnthropicProvider`, `GroqProvider` implementations that are never
exercised by tests in this environment (no API keys configured, and no
outbound network to those hosts in this sandbox). Provider selection is
`get_llm_provider()`, controlled by the `LLM_PROVIDER` env var, defaulting
to `mock`.

## Known limitations

- The Relationship Agent's independence check is document-id-based (same
  rule as `graph_service.independent_source_count`) -- it does not attempt
  semantic corroboration.
- The Contradiction Agent's heuristic (`MockProvider.detect_contradiction`)
  is a negation-cue/shared-vocabulary check, not real natural-language
  entailment -- it is explicitly documented as heuristic and always
  produces `REQUIRES_HUMAN_REVIEW`, never a final determination.
- The Issue Mapping Agent's heuristic (word-overlap between claim text and
  issue question) is simple by design; it is a *proposal* a human must
  approve, so a wrong guess costs a rejection, not a bad write.
