# NYAYA-SATYA Integration Contract

**Status: contract specification only.** This document describes how the
Case Bottleneck Engine will connect to the wider NYAYA-SATYA platform. It is
written to unblock that future integration — nothing in this file has been
implemented against a real Case Continuity Engine or Hearing Readiness
Engine, because those are separate projects (Project 02 and Project 01
respectively) that this repository does not contain. Where this document
says "will," it means "is specified but not yet built or tested against a
real counterpart."

## Where this engine sits

```
PROJECT 02 — CASE CONTINUITY ENGINE
    "What is the current evolving state of the case?"
        ↓  (Case Digital Twin / Continuity State)
PROJECT 03 — CASE BOTTLENECK ENGINE   ← this repository
    "Why is the case not progressing, what is the root bottleneck,
     what depends on it, and what safe action could move it forward?"
        ↓  (bottlenecks, root causes, safe actions, verification results)
PROJECT 01 — HEARING READINESS ENGINE
    "Is the case ready for the next hearing?"
        ↓
TARKA-VYUH — adversarial reasoning (deferred / Phase 2, per the platform's
own decision doc — see the Legal Backlog research report's Section 7/19)
        ↓
UNWIND — governance / audit
```

This engine answers a different question from Project 01 and Project 02 on
purpose (see the build spec's Section 3, "Differentiation from other
projects") — it is not a duplicate, and the three should exchange
*structured data*, not re-derive each other's conclusions.

## INPUT contract: what this engine expects to receive

This engine currently reads its own `Dependency` / `Transition` / `Case`
rows (populated today by `demo_data.py`'s synthetic cases, or by direct API
calls in a real deployment). To run against a real Case Continuity Engine,
that engine would need to produce, per case:

```jsonc
{
  "case_id": "string",
  "dependencies": [
    {
      "id": "string",
      "description": "string",
      "type": "document | filing | service | evidence | ...",
      "status": "SATISFIED | UNSATISFIED | UNKNOWN | CONTRADICTED",
      "depends_on": ["dependency_id", "..."],
      "evidence_refs": ["document_id", "..."],
      "since": "ISO-8601 timestamp or null"
    }
  ],
  "transitions": [
    {
      "id": "string",
      "name": "string",
      "prerequisite_dependency_ids": ["dependency_id", "..."]
    }
  ],
  "documents": [
    {
      "id": "string",
      "name": "string",
      "content_text": "string"
    }
  ]
}
```

This is a direct, intentionally minimal mapping of `models.py`'s
`Dependency`/`Transition`/`CaseDocument` tables (see Section 4/6 of the
model's own docstring for the full simplification list). A real Case
Continuity Engine's "Case Digital Twin" is expected to be considerably
richer (timeline events, structured claims, multilingual text); this
contract only specifies the subset the Bottleneck Engine actually consumes.
**Whatever produces this structured data — LLM extraction, OCR/NLP pipeline,
or manual entry — is explicitly out of scope for this engine**, which is why
Section 4 of the main README calls out "no LLM in this build" as the honest
limitation: this engine reasons over already-structured data, it does not
extract that structure from raw documents itself.

## OUTPUT contract: what this engine produces

Everything under `/api/cases/{id}/...` in the main README's API surface,
concretely:

```jsonc
{
  "bottlenecks": [ /* full Bottleneck rows — see models.py */ ],
  "root_cause_candidates": [ /* chain of {step, description, evidence, confidence} */ ],
  "dependencies_graph": { "nodes": [...], "edges": [...] },   // GET /flow
  "safe_actions": [ /* ActionItem rows, human-approval-gated */ ],
  "verification_results": [ /* VerificationRecord rows */ ],
  "bottleneck_history": [ /* BottleneckHistoryEntry rows */ ],
  "provenance": "every evidence_refs entry is a document_id the receiving system can resolve",
  "audit_records": [ /* AuditEvent rows, correlation_id-linked per investigation run */ ]
}
```

A downstream consumer (e.g. a Hearing Readiness Engine deciding whether a
case is ready for its next date) should treat an **open, high-confidence
bottleneck with an unresolved affected transition** as a strong "not ready"
signal, and a case with **zero open bottlenecks** as a weak "may be ready"
signal — weak, because this engine only checks the specific dependency
classes it models (Section 5's taxonomy), not the full readiness surface
(service completion, evidentiary sufficiency in the legal sense, etc.) that
a dedicated Hearing Readiness Engine would need to check independently.

## What would need to change for a real integration (honest gap list)

1. **A real Case Continuity Engine to call.** Today, `demo_data.py` plays
   that role. Swapping it for a real upstream system means writing an
   adapter that maps that system's Case Digital Twin shape into the
   `dependencies`/`transitions`/`documents` shape above — this adapter does
   not exist yet.
2. **Shared identifiers.** `case_id`, `dependency_id`, and `document_id`
   would need to be stable, shared primary keys across all three projects.
   Right now each project would mint its own IDs independently.
3. **A real evidence store.** `EvidenceVerificationAgent` currently checks
   whether a `CaseDocument` row exists in *this* database. In a real
   integration it would need to check against a shared evidence store or
   call out to the Case Continuity Engine's own store.
4. **Auth and multi-tenant isolation** between the three engines — this
   engine currently has no authentication layer at all (documented as a
   demo-scope limitation in the main README's security section).

None of the above is implemented. This document exists so that building it
later starts from an explicit, written contract instead of a guess.
