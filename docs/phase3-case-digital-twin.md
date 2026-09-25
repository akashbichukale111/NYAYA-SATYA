# NYAYA-SATYA — Phase 3: Case Digital Twin Specification
**CLAIM GRAPH + TIMELINE + EVIDENCE DEPENDENCY GRAPH**

> [!IMPORTANT]
> **NON-ADJUDICATION GUARANTEE**:
> This system structures and stress-tests evidence relationships. It does **not** determine judicial outcomes.
> NYAYA-SATYA does not predict verdicts, act as a judge, or determine guilt, fraud, perjury, liability, or legal victory.
> All reasoning proposals remain subject to the **Human Legal Gate** and UNWIND Core governance.

---

## 1. System Overview & Architecture

The **Case Digital Twin** represents the foundational, auditable bridge connecting three distinct operational planes:

```
  ┌────────────────────────────────────────────────────────┐
  │ 1. FACTUAL / PHYSICAL WORLD                           │
  │    - Entities (Persons, Orgs, Assets, Locations)       │
  │    - Timeline Events (Chronological stream)            │
  └───────────────────────────┬────────────────────────────┘
                              │ grounded by
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 2. EVIDENCE WORLD                                      │
  │    - SafeEvidenceRef (Sanitized, Content-Hashed)       │
  │    - Cryptographic ProvenanceDNA (SHA-256)             │
  │    - Contradiction Candidates (Phase 2 integration)    │
  └───────────────────────────┬────────────────────────────┘
                              │ supports / contradicts
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 3. LEGAL REASONING WORLD                              │
  │    - Structured Claims (SUPPORTED, CONTRADICTED)       │
  │    - Legal Issues & Unresolved Questions               │
  │    - Dependency Chains (DEPENDS_ON DAG)                │
  │    - Downstream Impact Analysis                        │
  └────────────────────────────────────────────────────────┘
```

---

## 2. Core Data Models

### 2.1 Entities (`nyaya_twin/contracts/entities.py`)
- **Types**: `PERSON`, `ORGANIZATION`, `LOCATION`, `ASSET`, `DOCUMENT`, `EVENT`, `OTHER`.
- **Status**: `VERIFIED_IDENTITY`, `POSSIBLE_MATCH`, `UNRESOLVED`, `ACTIVE`, `INACTIVE`.
- **Resolution Strategy**: Supports `EXACT_MATCH`, `ALIAS_MATCH`, `POSSIBLE_MATCH` (token overlap), and `UNRESOLVED`. Two similar names are never assumed to be the same person without corroboration.

### 2.2 Claims (`nyaya_twin/contracts/claims.py`)
- **Predicate-Object Structure**: `subject_entity_id`, `predicate`, `object_value`.
- **Status**: Strictly non-binary evidence states:
  - `SUPPORTED`: Backed by valid safe evidence references.
  - `PARTIALLY_SUPPORTED`: Backed by singular secondary evidence.
  - `CONTRADICTED`: Targeted by active evidence contradictions.
  - `UNSUPPORTED`: Zero supporting evidence registered.
  - `UNRESOLVED`: Under investigation.
  - `PENDING_REVIEW`: Awaiting human review.
- **Rule**: `TRUE` and `FALSE` judicial truth labels are structurally prohibited.

### 2.3 Issues (`nyaya_twin/contracts/issues.py`)
- Tracks disputed substantive matters: e.g. title ownership, payment timeliness, contractual breach.
- Links `related_claim_ids`, `related_evidence_ids`, and explicitly records `unresolved_questions`.

### 2.4 Timeline Events (`nyaya_twin/contracts/events.py`)
- **Precision**: `EXACT`, `DATE`, `MONTH`, `YEAR`, `RANGE`, `UNKNOWN`.
- **Anti-Fabrication**: Month/Year precisions strictly reject invented exact clock times (e.g. `2024-03-10T14:30:00Z` is rejected if declared `MONTH` or `YEAR`).
- **Temporal Conflict Detection**: Automatically detects when two assertions regarding the same event specify conflicting dates.

### 2.5 Relationships (`nyaya_twin/contracts/relationships.py`)
- Directed typed edges:
  - Evidence-to-Claim: `SUPPORTS`, `CONTRADICTS`, `MENTIONS`, `DERIVED_FROM`, `QUALIFIES`, `REFUTES`.
  - Claim-to-Claim: `DEPENDS_ON`, `CORROBORATES`, `CHALLENGES`.
  - Claim-to-Issue: `SUBMITTED_UNDER`, `RELEVANT_TO`.
  - Entity-to-Event/Claim: `PARTICIPATES_IN`, `SUBJECT_OF`.

### 2.6 Confidence Model (`nyaya_twin/contracts/confidence.py`)
- Replaces arbitrary fake percentages with explainable states: `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`.
- Provides human-readable basis statements (e.g. "Corroborated by 2 independent evidence references; Zero identified contradictions").

---

## 3. Graph Integrity & Validation (The 15 Rules)

Implemented in `nyaya_twin/validation/graph_validator.py`:

1. **Rule 1**: Every claim must reference a valid case identifier.
2. **Rule 2**: Every evidence reference must belong to the same case.
3. **Rule 3**: Every `SafeEvidenceRef` must pass hash integrity validation.
4. **Rule 4**: No claim may reference quarantined, un-cleared, or malicious evidence.
5. **Rule 5**: No graph node may reference nonexistent evidence.
6. **Rule 6**: No relationship may reference nonexistent source or target nodes.
7. **Rule 7**: No orphan provenance references with empty source/evidence IDs.
8. **Rule 8**: Strict cross-case isolation (Case A evidence cannot enter Case B).
9. **Rule 9**: No duplicate relationship identifiers.
10. **Rule 10**: Valid entity identifier format.
11. **Rule 11**: Impossible self-dependencies are rejected.
12. **Rule 12**: Dependency cycles on `DEPENDS_ON` edges are rejected via topological sort.
13. **Rule 13**: Timeline events must preserve declared time precision without timestamp invention.
14. **Rule 14**: Unknown timestamps must remain `UNKNOWN`.
15. **Rule 15**: Missing provenance is surfaced as `INCOMPLETE`.

---

## 4. Traversal & Impact Analysis

- **Evidence Querying**:
  - `get_supporting_evidence_for_claim(twin, claim_id)`
  - `get_contradicting_evidence_for_claim(twin, claim_id)`
  - `get_evidence_dependent_claims(twin, evidence_id)`
  - `get_unsupported_claims(twin)`
- **Claim Dependency Resolution**:
  - `get_claim_prerequisites(twin, claim_id)`: Direct prerequisites.
  - `get_claim_dependents(twin, claim_id)`: Direct dependents.
  - `get_claim_ancestors(twin, claim_id)`: Transitive upstream dependencies.
  - `get_claim_descendants(twin, claim_id)`: Transitive downstream dependencies.
- **Downstream Impact Analysis**:
  - `compute_evidence_invalidation_impact(twin, evidence_id)`: Quantifies the cascade of affected claims, issues, and events when an evidence item is invalidated or disputed.

---

## 5. REST API Endpoints

All endpoints are exposed under `/api/nyaya/cases/{case_id}/twin`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/nyaya/cases/{id}/twin/build` | Builds or updates twin from entities, claims, events, and registered safe evidence |
| `GET` | `/api/nyaya/cases/{id}/twin` | Retrieves high-level twin summary, integrity hash, and unresolved items |
| `GET` | `/api/nyaya/cases/{id}/twin/entities` | Lists registered entities and aliases |
| `GET` | `/api/nyaya/cases/{id}/twin/claims` | Lists claims, evidence states, and confidence |
| `GET` | `/api/nyaya/cases/{id}/twin/issues` | Lists legal issues and unresolved questions |
| `GET` | `/api/nyaya/cases/{id}/twin/timeline` | Returns chronological event sequence and temporal conflicts |
| `GET` | `/api/nyaya/cases/{id}/twin/graph` | Returns complete node and edge graph |
| `GET` | `/api/nyaya/cases/{id}/twin/evidence/{eid}/dependencies` | Analyzes downstream impact of evidence invalidation |
| `GET` | `/api/nyaya/cases/{id}/twin/claims/{cid}/support` | Queries supporting/contradicting evidence for a claim |
| `GET` | `/api/nyaya/cases/{id}/twin/claims/{cid}/dependencies` | Queries upstream/downstream claim dependencies |
| `GET` | `/api/nyaya/cases/{id}/twin/snapshot` | Exports deterministic, reproducible JSON snapshot |
| `POST` | `/api/nyaya/cases/{id}/twin/validate` | Validates twin against the 15 integrity rules |

---

## 6. Security & Governance Boundaries

1. **Quarantine Containment**: Raw byte payloads and quarantined documents are barred from the twin. Only registered `SafeEvidenceRef` bundles enter.
2. **Cross-Case Isolation**: Strong boundaries ensure evidence and claims from Case A cannot be linked into Case B.
3. **Execution Containment**: No code execution occurs on evidence content.
4. **UNWIND Core Alignment**: The twin provides structured reasoning context to TARKA-VYUH proposals, but cannot approve proposals. Approvals remain strictly reserved for the `HumanLegalGate`.

---

## 7. Known Limitations & Deferred Capabilities

The following capabilities are deliberately **not implemented** in Phase 3 and marked `NOT_IMPLEMENTED` in the capability registry:
- Full Causal Blast-Radius quantification (Deferred to Phase 4)
- Counterfactual Lab & What-If simulation (Deferred to Phase 4)
- Missing Evidence & Value-of-Information optimization (Deferred to Phase 4)
- Counterfactual Auto-Healer (Deferred to Phase 5)
- Independent Re-Attack and Repair Immunity (Deferred to Phase 5)
