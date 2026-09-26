# NYAYA-SATYA — Phase 8 Architecture & Production Security Specification

## 1. Executive Summary
Phase 8 solidifies NYAYA-SATYA as a hardened, production-ready, observable, privacy-first adversarial reasoning platform. It transitions the system from research-verified algorithms into an enterprise-grade service with zero trust, strong RBAC, immutable human approvals, multi-tenant case isolation, and comprehensive observability.

---

## 2. Architectural Pillars

```
                       ┌─────────────────────────────────────────┐
                       │           UNWIND Core Governance        │
                       │   (State Machine + Human Legal Gate)    │
                       └────────────────────┬────────────────────┘
                                            │ Human Decision
                                            ▼
┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
│     TARKA-VYUH Core     │───▶│   Reasoning Proposal    │───▶│     Execution Guard     │
│   (Adversarial Logic)   │    │   (Immutable SHA-256)   │    │  (Anti-Tamper Boundary) │
└─────────────────────────┘    └─────────────────────────┘    └─────────────────────────┘
             ▲                                                             │
             │                                                             ▼
┌─────────────────────────┐                                   ┌─────────────────────────┐
│     nyaya_evidence/     │                                   │   Governed Execution    │
│  (Quarantine + Parser)  │                                   │  (Audited Side Effects) │
└─────────────────────────┘                                   └─────────────────────────┘
             ▲
             │ Safe Evidentiary Representation
┌─────────────────────────┐
│  Untrusted Input Layer  │
│  (Size, MIME, Sandbox)  │
└─────────────────────────┘
```

---

## 3. Epistemic Classification & Non-Adjudication Integrity
In strict compliance with NYAYA-SATYA foundational principles:
- **No Autonomous Adjudication**: The system never issues judicial verdicts, predicts trial outcomes, or assigns guilt/liability.
- **Epistemic Classification**: Every metric and report is tagged with its provenance status:
  - `SYNTHETIC`: Generated from synthetic benchmark suites.
  - `OBSERVED`: Measured directly during interactive user sessions.
  - `ESTIMATED`: Projected from baseline/treatment comparative trials.
  - `PRIVATE_EVALUATION`: Measured within protected offline evaluation runs.
  - `REAL_DEPLOYMENT`: Sourced from authenticated production deployments.
- **Zero Fake Impact**: When no real deployment users have logged runs, deployment status explicitly states:
  `STATUS = NO_REAL_DEPLOYMENT_DATA_YET`.

---

## 4. Key Subsystems Delivered in Phase 8
1. **`nyaya_observability/`**:
   - Centralized metric collection, distributed request correlation (`X-Request-ID`), health (`/health`), readiness (`/ready`), versioning (`/version`), and audit logging.
2. **Security & RBAC Enforcement**:
   - Explicit permissions across 5 roles (`VIEWER`, `ANALYST`, `LEGAL_REVIEWER`, `GOVERNANCE_REVIEWER`, `ADMIN`).
   - Cross-case isolation barriers preventing multi-tenant data exposure.
3. **Hardened Evidence Quarantine & Ingestion**:
   - Max 15MB file cap, path traversal normalization, macro stripping, and safe decompression guards.
4. **Proposal Immutability Verification**:
   - Human approval cryptographically frozen against the proposal's SHA-256 digest. Post-approval changes immediately invalidate approval and block execution.
5. **Containerization & CI/CD Pipeline**:
   - Production multi-stage `Dockerfile` executing under unprivileged user `nyaya:10001` with built-in healthchecks.
