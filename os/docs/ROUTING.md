# NYAYA-SATYA OS — Complete Routing & Endpoint Table

This document maps all web routes and API endpoints across the OS Gateway and 12 modular engines.

---

## 1. Web Shell Routes

| Route | Description | View Rendered |
|---|---|---|
| `/` | OS Command Center | Consolidated Cockpit Dashboard |
| `/modules/{slug}` | Engine Deep View | Interactive Sub-View for specific engine |
| `/system-health-ui` | Diagnostics View | Live System Health & Safety Invariant Audit |

---

## 2. Core OS Gateway Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Core OS health check & safety invariant check |
| `GET` | `/system-health` | Detailed diagnostic audit across all 12 modules |
| `GET` | `/api/cockpit/summary` | Consolidated case context and 12 engine metrics |
| `GET` | `/api/cases` | List all cases in global case store |
| `GET` | `/api/cases/active` | Get active case context |
| `POST`| `/api/cases/switch?case_id={id}` | Switch active case context globally |
| `POST`| `/api/cases/{case_id}/authorize` | Human Legal Gate authorization signoff |
| `GET` | `/api/attention` | List prioritized cross-engine attention alerts |
| `POST`| `/api/attention/{id}/resolve` | Mark attention alert as resolved |
| `GET` | `/api/search?q={query}` | Global search across cases, engines, and rules |
| `GET` | `/api/events` | Cross-project event bus and audit trail log |

---

## 3. Module API Mounts

Each module is mounted under `/api/modules/{slug}`:

| # | Engine Slug | Key Endpoints Mounted |
|---|---|---|
| **01** | `hearing-readiness` | `GET /summary`, `GET /checklist`, `POST /actions/{id}/approve` |
| **02** | `case-continuity` | `GET /summary`, `GET /conflicts`, `POST /conflicts/{id}/resolve` |
| **03** | `case-bottleneck` | `GET /summary`, `GET /bottlenecks`, `POST /actions/{id}/approve` |
| **04** | `legal-aid-handoff` | `GET /summary`, `GET /dossier`, `GET /intake` |
| **05** | `procedural-obligation` | `GET /summary`, `GET /obligations`, `POST /obligations/{id}/sign` |
| **06** | `evidence-dependency` | `GET /summary`, `GET /graph`, `GET /claims` |
| **07** | `undertrial-liberty` | `GET /summary`, `GET /audit`, `POST /conflicts/{id}/resolve` |
| **08** | `registry-defect` | `GET /summary`, `GET /defects`, `POST /defects/{id}/verify` |
| **09** | `case-crash-test` | `GET /summary`, `POST /run-simulation`, `GET /scenarios` |
| **10** | `spark-personal-os` | `GET /summary`, `GET /digest`, `GET /notifications` |
| **11** | `spark-deadline-guardian`| `GET /summary`, `GET /deadlines`, `POST /ingest/text` |
| **12** | `spark-workflow-autopilot`| `GET /summary`, `GET /workflows`, `POST /tasks/{id}` |
