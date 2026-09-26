# NYAYA-SATYA — Security Controls Specification

## 1. Authentication Architecture
NYAYA-SATYA implements a fail-closed, multi-tier authentication resolver:
1. **Cloud Identity-Aware Proxy (IAP)**: Validates `x-goog-authenticated-user-email` when `UNWIND_TRUST_IAP_HEADER=1`.
2. **Bearer Token Authentication**: Evaluates `Authorization: Bearer <token>` against configured operator tokens (`UNWIND_OPERATOR_TOKENS`) using constant-time comparison (`hmac.compare_digest`).
3. **Explicit Dev Principal**: Available only when `UNWIND_ENV != production`. Refused in production by construction.
4. **Public Health Endpoints**: `/health`, `/ready`, `/version` are explicitly public to allow load balancers to poll service health without leaking secrets.

---

## 2. Role-Based Access Control (RBAC)
Every authenticated principal is mapped to one or more explicit roles:

| Role | Permitted Actions | Prohibited Actions |
|---|---|---|
| **`VIEWER`** | Read permitted case twins, view generated dossiers, view public impact summaries. | Cannot ingest evidence, run analysis, mutate twin, or approve proposals. |
| **`ANALYST`** | Ingest evidence, build digital twin, run gauntlets, execute causal counterfactuals, simulate repairs. | Cannot perform final human legal approval or execute consequential actions. |
| **`LEGAL_REVIEWER`** | Review proposals, approve or reject human checklist items, sign off on repaired cases. | Must be an authenticated human; service tokens are strictly rejected. |
| **`GOVERNANCE_REVIEWER`** | Audit state transitions, inspect cryptographic provenance chains, verify execution guard records. | Cannot bypass Human Legal Gate. |
| **`ADMIN`** | System configuration, service reset hooks (in dev/test), security parameter tuning. | Cannot bypass Human Legal Gate or fabricate evidence. |

---

## 3. Case-Level Isolation Barrier
Every case-scoped endpoint (`/api/nyaya/cases/{case_id}/*`) verifies tenant boundaries:
- The authenticated principal must hold explicit permission for the requested `case_id`.
- Principals with access to `CASE_ALPHA` are rejected with HTTP 403 Forbidden if attempting to access `CASE_BETA`.
- Repositories partition all data structures by `case_id` key:
  - Ingested evidence & quarantine store
  - Case digital twins
  - Adversarial gauntlet reports & assumption registries
  - Causal graphs & counterfactual scenarios
  - Repair candidates & simulated twins
  - Dossier version records & human review checklists
  - Impact telemetry events & benchmark results

---

## 4. Proposal Immutability & Human Gate Binding
To eliminate the risk of post-approval tampering:
1. When a proposal transitions to `ASK_HUMAN`, its exact content hash is computed:
   $$\text{proposal\_hash} = \text{SHA-256}(\text{claims} \parallel \text{evidence\_ids} \parallel \text{action} \parallel \text{provenance})$$
2. The jurist's decision record stores this `proposal_version_hash`.
3. Before `GovernedExecutor` executes any action, `ExecutionGuard` verifies:
   - Proposal status is `HUMAN_APPROVED`.
   - Decision record was signed by an authenticated human principal (`human::*`).
   - The current proposal hash **identically matches** `decision_record.proposal_version_hash`.
   - If any claim, evidence, or parameter changed in the interim, execution is immediately blocked with `ExecutionBlockedError`.

---

## 5. Rate Limiting & Compute Budget Protection
In-process token bucket rate limiting prevents compute exhaustion:
- **Standard Tier**: 60 requests / minute per principal for informational and read endpoints.
- **Expensive Operations Tier**: 10 requests / minute per principal for compute-heavy endpoints:
  - File upload & parsing
  - Adversarial gauntlet runs
  - Causal blast radius calculations
  - Multi-candidate repair simulation
  - 12-scenario synthetic benchmark execution
  - Dossier compilation
- Exceeded limits return HTTP 429 Too Many Requests with standard retry metadata.

---

## 6. HTTP & Transport Security Headers
Every HTTP response emitted by the API includes mandatory security headers:
- `X-Content-Type-Options: nosniff` (prevents MIME type sniffing)
- `X-Frame-Options: DENY` (prevents clickjacking)
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (in production)
- `X-Request-ID`: Unique correlation UUID for end-to-end request tracing.
