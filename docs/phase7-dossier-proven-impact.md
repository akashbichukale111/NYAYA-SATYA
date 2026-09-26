# Phase 7: Dossier 2.0 & Proven Impact Subsystem

## 1. Overview & Project Mandate

Phase 7 of **NYAYA-SATYA** introduces two pivotal production subsystems:
1. **Dossier 2.0**: The evolution of the Judicial Review Dossier into an immutable, versioned historical ledger featuring deterministic structural diffing (`DossierDiff`), SHA-256 semantic fingerprinting (independent of timestamps), and dedicated jurist review checklists (`HumanReviewChecklist`).
2. **Proven Impact Subsystem (`nyaya_impact/`)**: A rigorous, auditable, non-predictive structural evaluation framework. It delivers real, reproducible metrics across time efficiency, contradiction discovery, evidence gap detection, cryptographic provenance, repair effectiveness, and human gate friction without ever fabricating claims, user numbers, win rates, or predicting legal outcomes.

---

### Non-Negotiable Epistemic Principles

```
           ┌────────────────────────────────────────┐
           │      PROVEN IMPACT SUBSYSTEM           │
           ├────────────────────────────────────────┤
           │  • ZERO FAKE IMPACT                    │
           │  • STRICT EPISTEMIC CLASSIFICATION     │
           │  • PRIVACY MINIMIZATION (ZERO PII)     │
           │  • DETERMINISTIC REPRODUCIBILITY       │
           │  • ABSOLUTE NON-ADJUDICATION           │
           └────────────────────────────────────────┘
```

- **NO FAKE IMPACT**: Never fabricate customer numbers, hours saved, win probabilities, or artificial accuracy scores. All metrics are derived from verifiable graph structures or explicit simulations.
- **EPISTEMIC LABELS**: Every metric and report is tagged explicitly:
  - `OBSERVED`: Measured on live, actual pipeline executions.
  - `SYNTHETIC`: Evaluated against controlled synthetic benchmark scenarios.
  - `ESTIMATED`: Model-derived baselines (e.g., standard manual document review time).
  - `PRIVATE_EVALUATION`: Evaluated under strict NDA / private enterprise conditions.
  - `REAL_DEPLOYMENT`: Confirmed operational court/firm deployment data.
- **PRIVACY MINIMIZATION**: Structural events and measurements contain only opaque identifiers, hashes, counts, and latencies. PII (Aadhaar, PAN, phone numbers, email addresses, SSNs) is strictly rejected at the validation boundary.
- **NON-ADJUDICATION MANDATE**: The system does not predict verdicts, calculate win probabilities, or judge liability. The AI proposes, UNWIND Core governs, and the Human Legal Gate retains absolute decision authority.

---

## 2. Dossier 2.0 Architecture (`nyaya_dossier/`)

Dossier 2.0 ensures that judicial dossiers can evolve across litigation iterations while maintaining complete historical auditability.

```
       Dossier v1 (Build 1) ──► Fingerprint: SHA256_A
               │
               ▼ (Amendments / New Evidence / Simulated Repairs)
       Dossier v2 (Build 2) ──► Fingerprint: SHA256_B (prev: SHA256_A)
               │
               ├──► DossierComparator.compare(v1, v2) ──► DossierDiff (Added / Removed / Changed)
               │
               └──► DossierBuilder.build_human_checklist() ──► HumanReviewChecklist
```

### Components

1. **`DossierVersionRecord` & `DossierVersionStore`** (`dossier_version.py`):
   - Maintains an append-only sequential history of dossier versions for each case.
   - Links each version to its `previous_fingerprint`, creating an unbroken cryptographic hash chain.
2. **`DossierComparator` & `DossierDiff`** (`dossier_diff.py`):
   - Computes deterministic structural differences between any two version checkpoints across all 24 canonical sections.
   - Categorizes item transitions as `ADDED`, `REMOVED`, `CHANGED`, or `UNCHANGED`.
3. **`HumanReviewChecklist` & `ReviewItem`** (`human_checklist.py`):
   - Formulates explicit, actionable legal obligations requiring human jurist decision.
   - Assigns severity levels: `CRITICAL` (unresolved contradictions), `HIGH` (unsupported claims), `MEDIUM` (unverified legal authorities), `LOW` (minor administrative items).
   - Tracks human jurist interaction states: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `REJECTED`, `PENDING_HUMAN_DECISION`.
4. **Deterministic Semantic Fingerprinting** (`dossier_model.py`):
   - Dossier fingerprints compute SHA-256 over all 24 structural sections while strictly omitting volatile timestamps and transient UUIDs.

---

## 3. Proven Impact Subsystem Architecture (`nyaya_impact/`)

```
   ┌────────────────────────────────────────────────────────┐
   │                  TELEMETRY COLLECTION                  │
   │   EventCollector  │  SessionTracker  │  WorkflowTracker │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                  STRUCTURAL METRICS                    │
   │  Time  │ Contradiction │ Gap │ Provenance │ Repair     │
   │  Re-Attack │ Human Review Gate Interaction             │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │             EXPERIMENTS & COMPARATIVE TRIALS           │
   │   BaselineRunner (Control) vs TreatmentRunner (Nyaya)  │
   │   SyntheticBenchmarkSuite (12 Canonical Scenarios)     │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │             REPORTING & CRYPTOGRAPHIC EXPORTS          │
   │   ImpactReportCompiler (14-Section Proven Impact)      │
   │   ImpactSummaryGenerator (Executive KPIs)              │
   │   EvidenceExporter (Signed JSON Envelopes & Markdown)  │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                  SAFETY VALIDATION                     │
   │  MetricValidator │ ProvenanceValidator │ SafetyValidator│
   │  (No Fake Impact │ Privacy Minimized   │ Non-Adjudicate)│
   └────────────────────────────────────────────────────────┘
```

### 12 Canonical Synthetic Benchmark Scenarios

The `SyntheticBenchmarkSuite` executes 12 deterministic scenarios verifying structural robustness:
1. `BM_01_CONTRADICTION`: Direct mutual exclusion between evidence documents.
2. `BM_02_TIMELINE`: Pre-formation sequence anomaly in chronological events.
3. `BM_03_MISSING_EVIDENCE`: Unsupported corporate authorization requiring documentary proof.
4. `BM_04_UNSUPPORTED_ASSERTION`: Intent claims lacking documentary or oral corroboration.
5. `BM_05_PROVENANCE_BREAK`: Broken chain-of-custody and missing parent hash detection.
6. `BM_06_CAUSAL_DEPENDENCY`: Upstream claim revocation blast-radius propagation.
7. `BM_07_IRRELEVANT_PERTURBATION`: Formatting perturbation stability (Should-Not-Change).
8. `BM_08_MATERIAL_REMOVAL`: Critical fact removal dependency transition (Should-Change).
9. `BM_09_REPAIR_REGRESSION`: Collateral vulnerability detection during repair simulation.
10. `BM_10_PROMPT_INJECTION`: Hostile text injection defense ("Ignore instructions").
11. `BM_11_AUTHORITY_VERIFICATION`: Unverified citation downgrade to `AUTHORITY_UNVERIFIED`.
12. `BM_12_CROSS_CASE_ISOLATION`: Inter-case evidence attachment boundary rejection.

### The 14-Section Proven Impact Report

Every `ProvenImpactReport` implements 14 auditable sections:
1. Scope & Identity
2. Dataset & Sample Characteristics
3. Methodology & Epistemic Boundaries
4. Baseline Measurements (Control)
5. NYAYA-SATYA Workflow (Treatment)
6. Proven Impact Metrics
7. Comparative Trial Results
8. Structural Findings
9. Limitations & Threats to Validity
10. Reproducibility Protocol
11. Deployment & Evidence Classification
12. Human Review Gate Interactions
13. Privacy & Security Audit
14. Open Issues & Continuous Monitoring

---

## 4. API Endpoints

| Method | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/api/nyaya/cases/{case_id}/dossier/build` | Builds versioned dossier and records in version store |
| `GET` | `/api/nyaya/cases/{case_id}/dossier/latest` | Retrieves latest compiled judicial dossier |
| `GET` | `/api/nyaya/cases/{case_id}/dossier/versions` | Lists all historical dossier versions for a case |
| `GET` | `/api/nyaya/cases/{case_id}/dossier/versions/{v}` | Retrieves a specific historical dossier version |
| `POST` | `/api/nyaya/cases/{case_id}/dossier/diff` | Computes structural diff between two versions |
| `GET` | `/api/nyaya/cases/{case_id}/dossier/checklist` | Generates Human Review Checklist for the case |
| `POST` | `/api/nyaya/cases/{case_id}/impact/events` | Records immutable, privacy-minimized telemetry event |
| `GET` | `/api/nyaya/cases/{case_id}/impact/events` | Retrieves all telemetry events for a case |
| `POST` | `/api/nyaya/experiments/run` | Runs comparative trial (baseline vs treatment) on case twin |
| `POST` | `/api/nyaya/experiments/benchmark` | Runs the 12 canonical synthetic benchmark scenarios |
| `POST` | `/api/nyaya/cases/{case_id}/impact/report` | Compiles 14-section Proven Impact Report |
| `GET` | `/api/nyaya/cases/{case_id}/impact/report/latest` | Retrieves latest compiled impact report |
| `GET` | `/api/nyaya/cases/{case_id}/impact/report/export/json` | Exports cryptographically signed JSON envelope |
| `GET` | `/api/nyaya/cases/{case_id}/impact/report/export/markdown` | Exports structured Markdown with audit checksum |
| `GET` | `/api/nyaya/cases/{case_id}/impact/summary` | Generates high-level Executive KPIs |
| `POST` | `/api/nyaya/experiments/verify` | Verifies cryptographic integrity of an exported envelope |

---

## 5. Verification & Test Metrics

- **Phase 7 Test Suite**: `tests/test_nyaya_satya_phase7.py`
  - Total Tests: **38 passed, 0 failed**
  - Coverage: Versioning, Diffing, Checklists, Calculators, Comparative Trials, Synthetic Benchmarks, Reports, Summaries, Exporters, Safety Validators, and API routes.
- **Phase 6 Regression**: `tests/test_nyaya_satya_phase6.py`
  - Total Tests: **96 passed, 0 failed**
- **Full Repository Regression**:
  - **1,454 passed**, **159 skipped**, **0 failed** (170.97s)
