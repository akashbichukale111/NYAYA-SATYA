# NYAYA-SATYA — Production Deployment Guide

## 1. Architecture Overview
NYAYA-SATYA is packaged as a lightweight, secure containerized application deployed to Google Cloud Run (or any OCI-compliant container orchestration platform such as Kubernetes or AWS ECS).

```
                        [ HTTPS / TLS Termination ]
                                     │
                                     ▼
                        [ Cloud Armor / WAF Gate ]
                                     │
                                     ▼
                [ Google Identity-Aware Proxy (IAP) ]
                                     │
                                     ▼
               [ Cloud Run: NYAYA-SATYA Container ]
                   ├─ FastAPI Application Surface
                   ├─ TARKA-VYUH Reasoning Engine
                   ├─ UNWIND Core Governance Machine
                   ├─ Execution Guard & Human Gate
                   └─ Observability & Audit Logger
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
     [ Cloud Firestore ]    [ Cloud Pub/Sub ]   [ Secret Manager ]
      Case State Stores      Event Cascades      Operator Tokens
```

---

## 2. Environment Configuration Tiers

| Setting | Development (`dev`) | Testing (`test`) | Staging (`staging`) | Production (`production`) |
|---|---|---|---|---|
| `UNWIND_ENV` | `development` | `test` | `staging` | `production` |
| `UNWIND_DEV_PRINCIPAL` | Allowed (`dev-user`) | Allowed (`test-user`) | Disabled | Strictly Prohibited (raises 401) |
| `UNWIND_OPERATOR_TOKENS` | Local dummy tokens | Test runner tokens | Secret Manager mount | Secret Manager mount |
| `FIRESTORE_EMULATOR_HOST` | `localhost:8080` | `localhost:8080` | Disabled (Real Firestore) | Disabled (Real Firestore) |
| `UNWIND_TRUST_IAP_HEADER`| `0` | `0` | `1` | `1` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:*` | `http://testserver` | Specified staging URLs | Pinned production domain only |
| `RATE_LIMIT_WINDOW_SECONDS`| `60.0` | `60.0` | `60.0` | `60.0` |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `INFO` | `INFO` (JSON formatted) |

---

## 3. Container Specification (`docker/Dockerfile`)
- **Base Image**: `python:3.12-slim` (minimal attack surface, no unnecessary build utilities in final layer).
- **Non-Root Execution**: Runs as unprivileged user `nyaya:10001`.
- **Zero Baked Secrets**: No API keys, credentials, or `.env` files are included in the build context.
- **Healthcheck**: Periodically probes `GET /health` on port 8080.
- **Filesystem**: Read-only root filesystem with explicit ephemeral scratch space in `/tmp` and `.quarantine`.

---

## 4. Secret Manager Integration
Production operator tokens and signing keys are mounted securely from Google Cloud Secret Manager:
```bash
gcloud run deploy nyaya-satya \
  --source . \
  --set-secrets "UNWIND_OPERATOR_TOKENS=nyaya-operator-tokens:latest" \
  --set-env-vars "UNWIND_ENV=production,UNWIND_TRUST_IAP_HEADER=1"
```
No secrets are stored in environment variables directly or committed to the repository.
