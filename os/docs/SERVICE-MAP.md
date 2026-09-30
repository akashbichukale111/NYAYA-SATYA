# NYAYA-SATYA OS — Service Map & Port Strategy

This document details the process and port architecture for running NYAYA-SATYA OS.

---

## 1. Primary Operating Port

| Service | Host | Port | Entrypoint |
|---|---|---|---|
| **NYAYA-SATYA OS Gateway & Shell** | `127.0.0.1` | **8000** | `os/gateway/main.py:app` |
| **Legacy UNWIND Cockpit (Reference)** | `127.0.0.1` | **8080** | `services.api.nyaya:app` |

The OS Gateway runs on port **8000** by default, mounting all 12 modular engines and serving the unified shell at `http://127.0.0.1:8000`.

---

## 2. Standalone Development Ports (Optional Dev Mode)

When developing or testing engines individually in isolation:

| Engine | Standalone Port | Directory | Dev Command |
|---|---|---|---|
| 01 Hearing Readiness | `8001` | `os/modules/01-hearing-readiness` | `uvicorn backend.app.main:app --port 8001` |
| 02 Case Continuity | `8002` | `os/modules/02-case-continuity` | `uvicorn backend.app.main:app --port 8002` |
| 03 Case Bottleneck | `8003` | `os/modules/03-case-bottleneck` | `uvicorn backend.app.main:app --port 8003` |
| 04 Legal-Aid Handoff | `8004` | `os/modules/04-legal-aid-handoff` | `uvicorn backend.main:app --port 8004` |
| 05 Procedural Obligation | `8005` | `os/modules/05-procedural-obligation` | `uvicorn backend.app.main:app --port 8005` |
| 06 Evidence Dependency | `8006` | `os/modules/06-evidence-dependency` | `uvicorn backend.app.main:app --port 8006` |
| 07 Undertrial Liberty | `8007` | `os/modules/07-undertrial-liberty` | `uvicorn backend.app.main:app --port 8007` |
| 08 Registry Defect | `8008` | `os/modules/08-registry-defect` | `uvicorn backend.app.main:app --port 8008` |
| 09 Case Crash Test | `8009` | `os/modules/09-case-crash-test` | `uvicorn backend.app.main:app --port 8009` |
| 10 Spark Personal OS | `8010` | `os/modules/10-spark-personal-os` | `uvicorn backend.app.main:app --port 8010` |
| 11 Spark Deadline Guardian | `8011` | `os/modules/11-spark-deadline-guardian` | `uvicorn app.main:app --port 8011` |
| 12 Spark Workflow Autopilot | `8012` | `os/modules/12-spark-workflow-autopilot` | `uvicorn backend.app.api.main:app --port 8012` |

---

## 3. Production / Demo Unified Mode

In unified mode, launching `os/gateway/main.py` binds all 12 modules into a single fast async runtime on port `8000`, eliminating multi-process port collisions and allowing cross-module telemetry in microseconds.
