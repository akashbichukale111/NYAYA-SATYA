# NYAYA-SATYA OS — Global Case Context & State Synchronization

This document explains how global case context is managed, isolated, and synchronized across the 12 engines.

---

## 1. Single Source of Truth (`CaseStore`)

The `CaseStore` singleton (`os/shared/case_store.py`) maintains the authoritative in-memory and persistent records of all active cases.
At any point, one case is designated as the active case (`_active_case_id`).

### Seed Cases Provided:
1. `CASE-2024-DEL-0482`: **State v. Rajesh Kumar** (Criminal, Tis Hazari Court, Section 479 BNSS Undertrial Overdue Detention scenario).
2. `CASE-2023-BOM-1109`: **Apex Infrastructures v. Mumbai Port Trust** (Commercial Arbitration, Bombay High Court, Section 34 Evidence-heavy scenario).
3. `CASE-2024-KA-0077`: **Kaveri Farmers v. State of Karnataka** (Constitutional Writ Art. 226, Karnataka High Court, Registry Scrutiny Defect & Limitation scenario).

---

## 2. Dynamic Case Context Switching

When a user switches cases in the top OS bar:
1. Shell executes `POST /api/cases/switch?case_id={id}`.
2. `CaseStore` verifies the case exists, updates active pointer, and publishes an `EVT-SWITCH` event to the `EventBus`.
3. The shell reloads `/api/cockpit/summary`, instantly recalculating:
   - Custody duration vs 1/3rd sentence thresholds.
   - Specific filing scrutiny defects for the selected jurisdiction.
   - Upcoming statutory limitation deadlines.
   - Hearing readiness checklist items.
   - Evidence dependency DAG nodes.

---

## 3. Strict Case Isolation

No cross-case leakage occurs:
- Engine adapter queries require `case_id`.
- Attention items are indexed by `case_id`.
- Audit events log the originating `case_id`.
