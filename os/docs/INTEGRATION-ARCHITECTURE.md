# NYAYA-SATYA OS — Integration Architecture

This document describes the architectural design, component layers, data isolation, and communication patterns of the unified NYAYA-SATYA Operating System.

---

## Architectural Principles

1. **Monolithic Shell, Modular Engines**: A single unified OS command center shell provides consistent navigation, search, and context management, while each of the 12 engines retains its domain-specific internal logic, models, and boundaries.
2. **Non-Adjudication Invariant**: NYAYA-SATYA systems do not predict judicial outcomes, assign outcome probabilities, or make consequential judicial choices. The system audits procedural compliance, evidentiary dependencies, statutory rights, and timeline risks.
3. **UNWIND Human Legal Gate**: No automated consequential legal action (e.g. filing submission, counterparty communication, evidence withdrawal) is executed without human legal sign-off (`AWAITING_AUTHORISATION`).
4. **Single Source of Case Context**: The active case ID (`case_id`) is selected at the top OS level and propagated synchronously down to every engine adapter.

---

## System Layering

```
┌─────────────────────────────────────────────────────────────────┐
│               LAYER 1: UNIFIED OS SHELL (Frontend)              │
│  - Permanent Left Sidebar with Engine Navigation                │
│  - Top Command Bar: Global Case Switcher, Ctrl+K Search         │
│  - Cockpit Dashboard: 12 Interactive Engine Metric Cards        │
│  - Sub-Views: Deep Engine Telemetry, Graphs, & Checklists       │
│  - System Diagnostics & Health View (/system-health)            │
│  - Floating "✦ Personal AI" Copilot Assistant                   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP / JSON API
┌────────────────────────────────▼────────────────────────────────┐
│               LAYER 2: OS GATEWAY (FastAPI Router)              │
│  - Endpoint: /api/cockpit/summary (Consolidated Telemetry)      │
│  - Endpoint: /api/cases (Multi-tenant Case Management)          │
│  - Endpoint: /api/attention (Cross-Module Alert Aggregator)     │
│  - Endpoint: /api/search (Full-Text Search Service)             │
│  - Endpoint: /system-health (Real-Time Safety & Health Audit)   │
└──────────────────┬─────────────────────────────┬────────────────┘
                   │                             │
┌──────────────────▼─────────────┐ ┌─────────────▼────────────────┐
│ LAYER 3: ADAPTERS & CONTRACTS  │ │   LAYER 4: SHARED STATE      │
│  - HearingReadinessAdapter     │ │  - CaseStore (Multi-tenant)  │
│  - CaseContinuityAdapter       │ │  - AttentionCenter (Priority)│
│  - CaseBottleneckAdapter       │ │  - EventBus (Cross-Project)  │
│  - LegalAidHandoffAdapter      │ │  - ModuleRegistry (Metadata) │
│  - ProceduralObligationAdapter │ └──────────────────────────────┘
│  - EvidenceDependencyAdapter   │
│  - UndertrialLibertyAdapter    │
│  - RegistryDefectAdapter       │
│  - CaseCrashTestAdapter        │
│  - SparkPersonalOSAdapter      │
│  - SparkDeadlineGuardianAdapt. │
│  - SparkWorkflowAutopilotAdapt.│
└──────────────────┬─────────────┘
                   │ Internal Dispatch
┌──────────────────▼──────────────────────────────────────────────┐
│               LAYER 5: 12 ISOLATED ENGINE MODULES               │
│  os/modules/01-hearing-readiness                                │
│  os/modules/02-case-continuity                                  │
│  os/modules/03-case-bottleneck                                  │
│  os/modules/04-legal-aid-handoff                                │
│  os/modules/05-procedural-obligation (Grounded in settle/oblig.) │
│  os/modules/06-evidence-dependency                              │
│  os/modules/07-undertrial-liberty                               │
│  os/modules/08-registry-defect                                  │
│  os/modules/09-case-crash-test                                  │
│  os/modules/10-spark-personal-os                                │
│  os/modules/11-spark-deadline-guardian                          │
│  os/modules/12-spark-workflow-autopilot                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Isolation & Tenancy

All engine queries mandate a `case_id` parameter. State and database records are strictly partitioned by `case_id`. Cross-case queries are restricted to aggregate practice metrics in Module 10 (Spark Personal OS) and system diagnostic health.
