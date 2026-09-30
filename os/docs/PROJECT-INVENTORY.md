# NYAYA-SATYA OS — Complete Project Inventory

This document provides the authoritative inventory of all 12 modular engines integrated into the unified NYAYA-SATYA OS workspace at `D:\NYAYA-SATYA\os`.

---

## Executive Summary Matrix

| # | Engine Name | Category | Status | Backend Framework | Frontend Framework | Test Suite |
|---|---|---|---|---|---|---|
| **01** | Hearing Readiness Engine | Case Acceleration | **HEALTHY** | FastAPI (71 py files) | React + ReactFlow (31 files) | 11 test suites |
| **02** | Case Continuity Engine | Procedural & Compliance | **HEALTHY** | FastAPI (57 py files) | Web / API Rendered | 14 test suites |
| **03** | Case Bottleneck Engine | Case Acceleration | **HEALTHY** | FastAPI (32 py files) | React + React Router (13 files) | 6 test suites |
| **04** | Legal-Aid Handoff Engine | Human Rights & Liberty | **HEALTHY** | FastAPI (20 py files) | Web / Dossier Generator | 4 test suites |
| **05** | Procedural Obligation Engine | Procedural & Compliance | **PARTIAL / SEC 1** | FastAPI (Grounded in UNWIND) | Native Shell Card / Plain Text | 4 test suites |
| **06** | Evidence Dependency Engine | Evidence & Reasoning | **HEALTHY** | FastAPI (60 py files) | React + ReactFlow (25 files) | 13 test suites |
| **07** | Undertrial Liberty Sentinel | Human Rights & Liberty | **HEALTHY** | FastAPI (40 py files) | React + ReactFlow (16 files) | 8 test suites |
| **08** | Registry Defect Engine | Procedural & Compliance | **HEALTHY** | FastAPI (61 py files) | React + xyflow (19 files) | 19 test suites |
| **09** | Case Crash Test / Resilience Lab | Evidence & Reasoning | **HEALTHY** | FastAPI (34 py files) | React + ReactFlow (20 files) | 6 test suites |
| **10** | Spark Personal OS | Practice Automation | **HEALTHY / SEC 1** | FastAPI (29 py files) | React + Tailwind (7 files) | 5 test suites |
| **11** | Spark Deadline Guardian | Procedural & Compliance | **HEALTHY / SEC 1** | FastAPI (14 py files) | Web / Limitation Radar | 2 test suites |
| **12** | Spark Workflow Autopilot | Practice Automation | **HEALTHY** | FastAPI (42 py files) | Web / SOP Engine | 16 test suites |

---

## Detailed Module Inventories

### Module 01: Hearing Readiness Engine
- **Module ID**: `mod-01-hearing-readiness`
- **Slug**: `hearing-readiness`
- **Source Archive**: `hearing_readiness_engine.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/01-hearing-readiness/`
- **Files**: 122 total (71 Python files, 31 Frontend TSX/JSX files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /summary`
  - `GET /{case_id}`
  - `GET /{case_id}/actions`
  - `POST /{case_id}/actions/{action_id}/approve`
  - `GET /{case_id}/audit`
- **Frontend Stack**: Vite, React, ReactFlow, Framer Motion
- **Verification Status**: Fully operational.

### Module 02: Case Continuity Engine
- **Module ID**: `mod-02-case-continuity`
- **Slug**: `case-continuity`
- **Source Archive**: `case-continuity-engine.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/02-case-continuity/`
- **Files**: 72 total (57 Python files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /{case_id}/continuity-health`
  - `GET /{case_id}/conflicts`
  - `POST /{case_id}/conflicts/{conflict_id}/resolve`
  - `GET /{case_id}/changes`
- **Verification Status**: Fully operational.

### Module 03: Case Bottleneck Engine
- **Module ID**: `mod-03-case-bottleneck`
- **Slug**: `case-bottleneck`
- **Source Archive**: `case-bottleneck-engine.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/03-case-bottleneck/`
- **Files**: 55 total (32 Python files, 13 React files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /{case_id}/bottlenecks`
  - `GET /{case_id}/bottlenecks/{id}`
  - `POST /{case_id}/actions/{id}/approve`
- **Frontend Stack**: React, React Router
- **Verification Status**: Fully operational.

### Module 04: Legal-Aid Handoff Engine
- **Module ID**: `mod-04-legal-aid-handoff`
- **Slug**: `legal-aid-handoff`
- **Source Archive**: `legal-aid-handoff-engine.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/04-legal-aid-handoff/`
- **Files**: 29 total (20 Python files)
- **Primary Entry**: `backend/main.py`
- **Primary Routes**:
  - `GET /api/cases/{case_id}`
  - `GET /api/cases/{case_id}/intake`
  - `GET /api/cases/{case_id}/facts`
  - `GET /api/cases/{case_id}/documents`
- **Verification Status**: Fully operational.

### Module 05: Procedural Obligation Engine
- **Module ID**: `mod-05-procedural-obligation`
- **Slug**: `procedural-obligation`
- **Source Status**: `PARTIAL / SECTION 1 PRESENT`
- **Note on Source**: Exhaustive recursive disk search confirmed no separate zip archive existed on disk. Grounded directly in `unwind-live-verified-main/settle/obligation.py`.
- **Extracted / Implemented Location**: `os/modules/05-procedural-obligation/`
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /health`
  - `GET /api/cases/{case_id}/obligations`
  - `GET /api/obligations/{id}`
  - `POST /api/obligations/{id}/sign`
  - `GET /api/obligations/{id}/render`
- **Verification Status**: Cleanly integrated and verified via 4 automated unit tests.

### Module 06: Evidence Dependency Engine
- **Module ID**: `mod-06-evidence-dependency`
- **Slug**: `evidence-dependency`
- **Source Archive**: `evidence-dependency-engine.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/06-evidence-dependency/`
- **Files**: 109 total (60 Python files, 25 Frontend TSX files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /cases/{case_id}/dependency-graph`
  - `GET /cases/{case_id}/claims`
  - `GET /cases/{case_id}/evidence`
  - `GET /cases/{case_id}/coverage`
- **Frontend Stack**: React, ReactFlow, TanStack React Query, Zod
- **Verification Status**: Fully operational.

### Module 07: Undertrial Liberty Sentinel
- **Module ID**: `mod-07-undertrial-liberty`
- **Slug**: `undertrial-liberty`
- **Source Archive**: `undertrial-liberty-sentinel.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/07-undertrial-liberty/`
- **Files**: 98 total (40 Python files, 16 React TSX files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /cases/{case_id}/attention`
  - `GET /cases/{case_id}/review-queue`
  - `GET /cases/{case_id}/verification`
  - `POST /conflicts/{conflict_id}/resolve`
- **Frontend Stack**: React, ReactFlow, Framer Motion, Axios
- **Verification Status**: Fully operational.

### Module 08: Registry Defect Engine
- **Module ID**: `mod-08-registry-defect`
- **Slug**: `registry-defect`
- **Source Archive**: `registry-defect-engine.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/08-registry-defect/`
- **Files**: 111 total (61 Python files, 19 React TSX files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /api/cases/{case_id}/filing-packages`
  - `GET /api/defects/{id}`
  - `GET /api/defects/{id}/impact`
  - `GET /api/defects/{id}/suggested-correction`
  - `POST /api/defects/{id}/verify`
- **Frontend Stack**: React, xyflow, TanStack React Query, Zod
- **Verification Status**: Fully operational.

### Module 09: Case Crash Test / Resilience Lab
- **Module ID**: `mod-09-case-crash-test`
- **Slug**: `case-crash-test`
- **Source Archive**: `case-crash-test.tar.gz` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/09-case-crash-test/`
- **Files**: 168 total (34 Python files, 20 React TSX files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /cases/{case_id}/scenarios`
  - `GET /cases/{case_id}/graph`
  - `POST /cases/{case_id}/nodes`
  - `POST /api/demo/load`
- **Frontend Stack**: React, ReactFlow, TanStack Query
- **Verification Status**: Fully operational.

### Module 10: Spark Personal OS
- **Module ID**: `mod-10-spark-personal-os`
- **Slug**: `spark-personal-os`
- **Source Archive**: `spark-personal-os-section1.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/10-spark-personal-os/`
- **Files**: 62 total (29 Python files, 7 React TSX files)
- **Primary Entry**: `backend/app/main.py`
- **Primary Routes**:
  - `GET /api/cases/{case_id}/digest`
  - `GET /api/notifications`
  - `GET /api/saved-views`
  - `POST /api/notifications/{id}/read`
- **Verification Status**: Verified Section 1 operational status.

### Module 11: Spark Deadline Guardian
- **Module ID**: `mod-11-spark-deadline-guardian`
- **Slug**: `spark-deadline-guardian`
- **Source Archive**: `spark-deadline-guardian-section1.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/11-spark-deadline-guardian/`
- **Files**: 17 total (14 Python files)
- **Primary Entry**: `app/main.py`
- **Primary Routes**:
  - `GET /deadlines`
  - `GET /deadlines/{id}`
  - `POST /ingest/text`
  - `POST /deadlines/{id}/review`
- **Verification Status**: Verified Section 1 operational status.

### Module 12: Spark Workflow Autopilot
- **Module ID**: `mod-12-spark-workflow-autopilot`
- **Slug**: `spark-workflow-autopilot`
- **Source Archive**: `spark-workflow-autopilot.zip` (Preserved in `os/archives/`)
- **Extracted Location**: `os/modules/12-spark-workflow-autopilot/`
- **Files**: 67 total (42 Python files)
- **Primary Entry**: `backend/app/api/main.py`
- **Primary Routes**:
  - `GET /api/cases/{case_id}/workflows`
  - `GET /api/workflows/{id}`
  - `POST /api/tasks/{task_id}`
  - `GET /api/templates`
- **Verification Status**: Fully operational.
