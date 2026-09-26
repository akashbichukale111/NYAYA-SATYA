# NYAYA-SATYA — Phase 8 Security & Deployment Repository Audit

## Executive Summary
This comprehensive audit evaluates the NYAYA-SATYA adversarial reasoning codebase as of Phase 7 (commit `1e1a771`). It inventories all architectural layers, data flows, storage surfaces, credential paths, and governance boundaries to establish the security baseline for production deployment.

---

## 1. Subsystem Audit Matrix

| Subsystem | Core Functionality | Security / Governance Boundary | Audit Findings & Hardening Need |
|---|---|---|---|
| **`nyaya_evidence/`** | Ingestion, quarantine, adversarial sanitization, parsers | Quarantine isolation, untrusted input barrier | Needs strict size caps (15MB), path normalization, decompression limits, and MIME validation. |
| **`nyaya_twin/`** | Case Digital Twin, claim/evidence dependency graphs | Data structure integrity, twin hashing | Isolated in-memory per case ID; requires explicit cross-case isolation checks at API boundary. |
| **`nyaya_adversarial/`** | Conflict Arena, Gauntlet, Jenga fragility, VOI | Reasoning isolation, deterministic attack rules | Purely analytical; cannot modify twin directly. Depends on validated twin. |
| **`nyaya_causal/`** | Causal graphs, counterfactual interventions, blast radius | Clone twin isolation for interventions | Ensures interventions occur strictly on isolated twin clones. |
| **`nyaya_repair/`** | Auto-healer, repair candidates, utility vector | Simulation isolation, hard constraints | Proposes repairs; strictly forbidden from autonomous approval or execution. |
| **`nyaya_reattack/`** | Independent re-attack, immunity assessment | Adversarial independence | Re-attacks post-repair twins independently without trusting repair generator. |
| **`nyaya_perturbation/`** | Perturbation lab (Should-Change / Should-Not-Change) | Structural stability evaluation | Evaluates stability without making legal outcome predictions. |
| **`nyaya_readiness/`** | Case readiness snapshot and delta calculator | Non-adjudication guarantee | Measures structural graph readiness; never outputs win probability or guilt scores. |
| **`nyaya_dossier/`** | Judicial Review Dossier 2.0, versioning, diff, checklist | Auditability and human review queue | Enforces deterministic semantic hashing; checklist items require human jurist sign-off. |
| **`nyaya_impact/`** | Proven Impact subsystem, 12 benchmarks, 14-section report | Privacy minimization, zero fake impact | Validates zero PII (Aadhaar, PAN, phone, email, SSN); strictly enforces epistemic status tags. |
| **`unwind_core/`** | Governance state machine, Human Legal Gate, Execution Guard | Sole consequential authority | Enforces human approval binding via `proposal_version_hash`. Forbids automated self-approval. |
| **`tarka_vyuh/`** | Reasoning proposals, cryptographic provenance | Cryptographic lineage tracking | Mandatory SHA-256 provenance hashes on all proposed actions. |
| **`services/api/`** | FastAPI routes (`main.py`, `nyaya.py`, `security.py`) | Public / Protected / Admin perimeter | Needs explicit RBAC (`VIEWER` to `ADMIN`), cross-case access controls, and rate-limiting tiers. |

---

## 2. Secrets & Credential Handling Audit
- **Git Exclusions**: Verified that `.env`, `*.pem`, `*-key.json`, `.quarantine/`, `.sandbox/`, and `.media/` are excluded in `.gitignore`.
- **Strengthening Needed**: Explicitly add `*.key`, `*.p12`, `*.pfx`, `secrets/`, and `.secrets/` to `.gitignore`.
- **Hardcoded Secrets**: Verified zero hardcoded RSA/EC/DSA/OPENSSH keys in git tree. All tokens parse dynamically via `UNWIND_OPERATOR_TOKENS` and `UNWIND_HUMAN_TOKENS`.
- **Production Mode Safety**: In `UNWIND_ENV=production`, `UNWIND_DEV_PRINCIPAL` is rejected by construction.

---

## 3. Authentication & Authorization Baseline
- **Existing**: `lib/auth.py` provides IAP header validation (`x-goog-authenticated-user-email`), bearer token constant-time parsing (`hmac.compare_digest`), and dev principal fallback (dev only).
- **Existing Gate**: `tests/test_api_auth.py` strictly verifies that every mutating endpoint (`POST`, `PUT`, `PATCH`, `DELETE`) enforces `require_principal` or `require_human_principal`.
- **Phase 8 Hardening**:
  - Add explicit Role-Based Access Control (`Role.VIEWER`, `Role.ANALYST`, `Role.LEGAL_REVIEWER`, `Role.GOVERNANCE_REVIEWER`, `Role.ADMIN`).
  - Add Case-Level Authorization (`require_case_access`): A user authenticated for `CASE_001` cannot read, write, or query `CASE_002`.

---

## 4. File Upload & Ingestion Security
- Untrusted files enter through `nyaya_evidence/ingestion/ingest.py`.
- Files are quarantined under `.quarantine/` before any parsing.
- Parsers (`pdf`, `docx`, `csv`, `json`, `text`) execute in strict isolation.
- Phase 8 Hardening:
  - Path traversal checks (rejecting `../`, `..\\`, absolute paths, null bytes).
  - Maximum upload size cap: 15MB.
  - Archive decompression limit: max 100 entries, max 50MB uncompressed ratio limit.

---

## 5. Telemetry & Privacy Audit
- Phase 7 introduced privacy-minimized telemetry (`EventCollector`) and safety validation (`ImpactSafetyValidator`).
- Regex validation rejects:
  - Indian Aadhaar (12 digits)
  - Indian PAN (`[A-Z]{5}[0-9]{4}[A-Z]`)
  - Phone numbers (10 digits)
  - Email addresses
  - US SSN (`\d{3}-\d{2}-\d{4}`)
- Telemetry stores only anonymized structural event types, durations, and cryptographic provenance hashes. No raw case evidence enters telemetry.

---

## 6. Observability & Monitoring Baseline
- Current logging relies on basic console output or OpenTelemetry if configured.
- Phase 8 Hardening:
  - Structured JSON logging with request correlation (`X-Request-ID`).
  - Dedicated package `nyaya_observability/` providing request metrics, health status (`/health`), readiness assessment (`/ready`), and application version information (`/version`).
  - Consequential audit log emitter recording all security, governance, and review actions.
