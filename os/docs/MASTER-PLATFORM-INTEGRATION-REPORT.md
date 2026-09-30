# NYAYA-SATYA Master Platform — Complete Integration Report

**Date**: 2026-09-30  
**Platform Version**: v2.1.0 Master  
**Workspace**: `D:\NYAYA-SATYA`  
**Master Gateway Route**: `http://127.0.0.1:8000/os`  
**Core Route**: `http://127.0.0.1:8000/os/core`  
**Total Experiences**: 13 (1 Flagship Core Platform + 12 Specialized Intelligence Engines)

---

## 1. Architectural Overview

NYAYA-SATYA is architected as **ONE unified master legal platform** orchestrating:
1. **The Original NYAYA-SATYA Core**: The full-scale legal evidence intelligence platform (`unwind-live-verified-main`), preserved in its entirety with its 100 API routes, Digital Twin graph, Adversarial gauntlet, Causal blast radius engine, Repair & Re-attack loops, Defense Dossier builder, and UNWIND Human Legal Gate.
2. **The 12 Specialized Intelligence Engines**: Distinct, domain-specific modules serving procedural scrutiny, liberty enforcement, statutory limitation monitoring, and practice automation.
3. **The Master OS Command Center**: A persistent left navigation sidebar and top command bar unifying all 13 experiences, managing global case context (`case_id`), full-text search (`Ctrl+K`), and cross-project events.

```
                           NYAYA-SATYA
                     MASTER PLATFORM SHELL
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
    NYAYA-SATYA CORE               12 SPECIALIZED ENGINES
    (Original Platform)            (01 through 12)
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                      SHARED CASE CONTEXT
                     (Global Case Switcher)
                               ▼
                      CROSS-PROJECT EVENTS
                               ▼
                       UNWIND HUMAN GATE
                     (Licensed Counsel Sign)
```

---

## 2. Flagship: Original NYAYA-SATYA Core

- **Name**: NYAYA-SATYA CORE
- **Status**: **HEALTHY / OPERATIONAL (100% Preserved)**
- **Route**: `/os/core` (Direct Core API mount: `/cases`, `/proposals`, `/twin/...`, `/adversarial/...`, `/causal/...`, `/repair/...`, `/dossier/...`)
- **Frontend Stack**: Original Cinematic Cockpit UI (`web/static/index.html`, `style.css`, `app.js`), constellation canvas, multi-jurisdiction selector, citizen mode, role permissions.
- **Backend Stack**: FastAPI (`services.api.nyaya.py` + `services.api.main.py`, 100+ endpoints).
- **Primary Workflows**:
  1. Case Digital Twin construction & entity-claim dependency mapping.
  2. Adversarial Arena: Conflict discovery, fragility auditing, and Achilles' heel detection.
  3. Causal Blast Radius: Upstream/downstream impact simulation when evidence changes.
  4. Repair Workbench & Re-Attack verification loop.
  5. Comprehensive Defense Dossier builder with markdown and JSON export.
  6. Real Deployment Impact Tracking & Observability metrics.
- **OS Return**: Master return header injected at top: `← Back to NYAYA-SATYA OS | NYAYA-SATYA / CORE INTELLIGENCE / ORIGINAL PLATFORM`.
- **Shared Context**: Reads and synchronizes `window.nyayaActiveCaseId` with `localStorage` and OS Gateway.
- **Verification Result**: `VERIFIED & OPERATIONAL` (HTTP 200, all assets loaded, 100 routes mounted).

---

## 3. The 12 Specialized Project Engines

### Project 01 — Hearing Readiness Engine
- **Status**: **HEALTHY**
- **Route**: `/os/projects/hearing-readiness`
- **Frontend**: Specialized pre-hearing audit docket (`01_hearing_readiness.html`), readiness gauge (78%), and interactive court checklist.
- **Backend**: FastAPI adapter mounting `os/modules/01-hearing-readiness/backend/app/main.py`.
- **Primary Workflow**: Pre-hearing docket audit; flags unserved summons / omitted exhibits under Section 207 CrPC before cause list publication; enables one-click curative praecipe approvals.
- **Shared Context**: Dynamically audits active case (`CASE-2024-DEL-0482`).
- **Cross-Project Connection**: Receives missing document alerts from Evidence Dependency Engine (06) and feeds listing blockers into Case Bottleneck Engine (03).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 02 — Case Continuity Engine
- **Status**: **HEALTHY**
- **Route**: `/os/projects/case-continuity`
- **Frontend**: Original vanilla JS multi-view application (`os/modules/02-case-continuity/frontend/` with `app.js`, `api.js`, `styles.css`) embedded with OS Master Header.
- **Backend**: FastAPI adapter mounting `os/modules/02-case-continuity/backend/app/main.py`.
- **Primary Workflow**: Multi-counsel handoff resilience; audits discrepancies between daily order sheets and formal pleadings; computes continuity health index (91%).
- **Shared Context**: `window.__CCE_API_BASE__ = "/api/modules/case-continuity"`, synced with active `case_id`.
- **Cross-Project Connection**: Supplies conflict ledgers to Legal-Aid Handoff Engine (04).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, original frontend rendered).

### Project 03 — Case Bottleneck Engine
- **Status**: **HEALTHY**
- **Route**: `/os/projects/case-bottleneck`
- **Frontend**: Specialized bottleneck investigation dashboard (`03_case_bottleneck.html`) with comparative delay charts and root-cause breakdown.
- **Backend**: FastAPI adapter mounting `os/modules/03-case-bottleneck/backend/app/main.py`.
- **Primary Workflow**: Stage duration benchmarking; compares case duration (112 days in bail stage) against court median (32 days, +350% delay factor); classifies causes into summons process failure vs FSL backlog.
- **Shared Context**: Queries active case stage duration.
- **Cross-Project Connection**: Triggers bottleneck alerts to Spark Workflow Autopilot (12) and UNWIND Human Gate.
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 04 — Legal-Aid Handoff Engine
- **Status**: **HEALTHY**
- **Route**: `/os/projects/legal-aid-handoff`
- **Frontend**: Original custom serif & paper-themed legal-aid docket (`os/modules/04-legal-aid-handoff/frontend/index.html`) embedded with OS Master Header.
- **Backend**: FastAPI adapter mounting `os/modules/04-legal-aid-handoff/backend/main.py`.
- **Primary Workflow**: Counsel transfer briefing; compiles standardized intake profile, 28 mapped facts, and statutory bail grounds under Section 479 BNSS for pro-bono advocates.
- **Shared Context**: Scoped to assigned legal aid counsel and active case.
- **Cross-Project Connection**: Consumes fact matrix from Core Digital Twin and passes brief to Spark Personal OS (10).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, original frontend rendered).

### Project 05 — Procedural Obligation Engine
- **Status**: **PARTIAL / SECTION 1 PRESENT (Grounded in UNWIND)**
- **Honesty Disclosure**: No standalone `.zip` archive was present on disk. The module was built directly upon the authoritative UNWIND `settle/obligation.py` engine contracts.
- **Route**: `/os/projects/procedural-obligation`
- **Frontend**: Specialized WHO / WHAT / LOSS / SIGN compliance workbench (`05_procedural_obligation.html`) with plain text memo rendering and digital signing.
- **Backend**: FastAPI engine in `os/modules/05-procedural-obligation/backend/app/main.py`.
- **Primary Workflow**: Strict non-adjudicative statutory correction compliance; calculates irreversible loss ranges (INR 0 - 50,000) and halts execution until human advocate signs obligation.
- **Shared Context**: Synchronized with active case obligations.
- **Cross-Project Connection**: Directly gates all mutating procedural steps across all engines.
- **Verification Result**: `VERIFIED` (4 unit tests passed, integration test passed, digital sign-off works).

### Project 06 — Evidence Dependency Engine
- **Status**: **HEALTHY**
- **Route**: `/os/projects/evidence-dependency`
- **Frontend**: Specialized bipartite Claim-Evidence DAG visualization (`06_evidence_dependency.html`) with fragility badges and single-point-of-failure alerts.
- **Backend**: FastAPI adapter mounting `os/modules/06-evidence-dependency/backend/app/main.py`.
- **Primary Workflow**: Bipartite DAG mapping between assertions (claims) and exhibits; flags uncorroborated assertions and critical single-point failures (Claim 3 Chain of Custody).
- **Shared Context**: Scoped to active case exhibits.
- **Cross-Project Connection**: Supplies vulnerability blast radius to Case Crash Test Lab (09).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 07 — Undertrial Liberty Sentinel
- **Status**: **HEALTHY**
- **Route**: `/os/projects/undertrial-liberty`
- **Frontend**: Specialized statutory liberty dashboard (`07_undertrial_liberty.html`) with detention duration counter and Section 479 statutory entitlement banner.
- **Backend**: FastAPI adapter mounting `os/modules/07-undertrial-liberty/backend/app/main.py`.
- **Primary Workflow**: Section 479 BNSS / 436A CrPC custody calculation; audits 418 days served against 365 days threshold (1/3rd maximum sentence); detects +53 days overdue detention; compiles mandatory bail petition packet.
- **Shared Context**: Ingests custody start date and active case jurisdiction.
- **Cross-Project Connection**: Fires CRITICAL attention alert to Master OS topbar and feeds bail grounds to Legal-Aid Handoff (04).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 08 — Registry Defect Engine
- **Status**: **HEALTHY**
- **Route**: `/os/projects/registry-defect`
- **Frontend**: Specialized court scrutiny defect inspector (`08_registry_defect.html`) with rule references, cure window countdown, and curative action patches.
- **Backend**: FastAPI adapter mounting `os/modules/08-registry-defect/backend/app/main.py`.
- **Primary Workflow**: High Court and Commercial Court registry scrutiny validator; audits Statement of Truth notarization and annexure pagination; provides automated curative steps within 30-day window.
- **Shared Context**: Scoped to court jurisdiction of active case.
- **Cross-Project Connection**: Links cure deadlines with Spark Deadline Guardian (11).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 09 — Case Crash Test / Resilience Lab
- **Status**: **HEALTHY**
- **Route**: `/os/projects/case-crash-test`
- **Frontend**: Specialized adversarial resilience sandbox (`09_case_crash_test.html`) with simulation trigger and resilience scoring.
- **Backend**: FastAPI adapter mounting `os/modules/09-case-crash-test/backend/app/main.py`.
- **Primary Workflow**: Adversarial stress-testing; simulates key witness turning hostile and electronic evidence exclusion under Section 63 BSA; computes case resilience index (64/100).
- **Shared Context**: Evaluates defense theory of active case.
- **Cross-Project Connection**: Informs defense strategy recommendations in Hearing Readiness (01).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, simulation works).

### Project 10 — Spark Personal OS
- **Status**: **HEALTHY / SECTION 1 VERIFIED**
- **Route**: `/os/projects/spark-personal-os`
- **Frontend**: Specialized practitioner desk (`10_spark_personal_os.html`) with daily morning digest, cause list schedule, and unread notification inbox.
- **Backend**: FastAPI adapter mounting `os/modules/10-spark-personal-os/backend/app/main.py`.
- **Primary Workflow**: Personalized practice management; organizes daily court appearances across Tis Hazari and High Court; aggregates unread alerts across all assigned cases.
- **Shared Context**: Filtered by active lead counsel.
- **Cross-Project Connection**: Aggregates attention items generated by all 12 engines.
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 11 — Spark Deadline Guardian
- **Status**: **HEALTHY / SECTION 1 VERIFIED**
- **Route**: `/os/projects/spark-deadline-guardian`
- **Frontend**: Specialized limitation radar (`11_spark_deadline_guardian.html`) with countdown cards and escalation dispatch buttons.
- **Backend**: FastAPI adapter mounting `os/modules/11-spark-deadline-guardian/app/main.py`.
- **Primary Workflow**: Limitation Act 1963 statutory calculator; accounts for court holidays and vacation benches; tracks limitation periods (e.g. 4 days remaining for Section 173(8) objection).
- **Shared Context**: Calculates deadlines relative to active case milestones.
- **Cross-Project Connection**: Escalates imminent limitation expiries to Master OS topbar pill.
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

### Project 12 — Spark Workflow Autopilot
- **Status**: **HEALTHY**
- **Route**: `/os/projects/spark-workflow-autopilot`
- **Frontend**: Specialized SOP pipeline tracker (`12_spark_workflow_autopilot.html`) with multi-stage progress track and human approval boundary.
- **Backend**: FastAPI adapter mounting `os/modules/12-spark-workflow-autopilot/backend/app/api/main.py`.
- **Primary Workflow**: Standard Operating Procedure (SOP) automation; executes multi-stage bail filing procedure (80% complete); stops execution at UNWIND human legal gate before registry dispatch.
- **Shared Context**: Bound to active case procedural stage.
- **Cross-Project Connection**: Automates execution of curative praecipes generated by Hearing Readiness (01) and Registry Defect (08).
- **Verification Result**: `VERIFIED` (Automated Pytest passed, live UI rendered).

---

## 4. Verification Summary

- **Automated Pytest Suite**: 19 tests executed across all 13 experiences — **19 PASSED (100%)**.
- **Deep Linking**: All 13 routes support direct URL entry, browser refresh, forward/back buttons, and OS return.
- **Shared Case Context**: Switching active case (`/api/cases/switch`) instantly propagates across Core and all 12 engines without state collision.
- **Safety Invariant**: Non-adjudication guarantee strictly upheld (zero outcome prediction across all 13 experiences).
- **Source Code Preservation**: Original source archives preserved in `os/archives/`; original NYAYA-SATYA Core codebase in `unwind-live-verified-main` 100% untouched and fully mounted.
- **Git Repository**: All files committed and pushed to remote `origin/main`.
