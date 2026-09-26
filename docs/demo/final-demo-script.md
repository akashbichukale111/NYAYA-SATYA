# NYAYA-SATYA — Final Hackathon Demonstration Script (2–3 Minutes)

> **IMPORTANT NOTICE**:  
> **SYNTHETIC DEMONSTRATION CASE — NOT REAL EVIDENCE AND NOT A LEGAL VERDICT.**  
> NYAYA-SATYA is an adversarial reasoning and evidence analysis system. It does not predict judicial verdicts, decide legal guilt, or replace qualified legal counsel. Consequential actions require Human Legal Gate authorization.

---

## Executive Overview
- **Product**: NYAYA-SATYA (Adversarial Evidence & Case Reasoning System)
- **Target Audience**: Hackathon Judges, Legal Technologists, AI Safety Researchers
- **Duration**: 2 Minutes 45 Seconds (165 Seconds)
- **Demonstration Case ID**: `CASE_SYNTHETIC_DEMO_2026`

---

## Timing & Stage-by-Stage Script Flow

### [0:00 – 0:20] 1. The Problem: Fragmented Evidence & Fragile Drafts
- **Spoken Narrative**:
  > "In legal disputes, critical facts are fragmented across dozens of exhibits, dates, and statements. Traditional LLMs act like agreeable drafting assistants—they generate polished text that glosses over critical contradictions. When a draft relies on unverified assumptions, a single opposing exhibit can collapse the entire argument in court. NYAYA-SATYA takes the opposite approach: **Don't trust the draft. Attack it. Repair it. Attack the repair.**"
- **Visual**:
  - Show the **NYAYA-SATYA Mission Cockpit** (`docs/assets/nyaya-satya-main-screen.png`).
  - Point to the active case status and empty timeline awaiting adversarial verification.

---

### [0:20 – 0:40] 2. Secure Evidence Ingestion & Case Digital Twin
- **Spoken Narrative**:
  > "We ingest our case documents. Upload protection validates MIME types, enforces size caps, scrubs directory traversal, and scans for adversarial prompt injections. From these documents, NYAYA-SATYA constructs a Case Digital Twin—a formal bipartite graph linking entities, dates, claims, and exact source spans with SHA-256 provenance hashes."
- **Visual**:
  - Ingestion of synthetic exhibits:
    - **Exhibit E17**: Vendor shipment memo stating: *"Material dispatched on 12 March 2026."*
    - **Exhibit E22**: Freight receipt stating: *"Consignment accepted at freight hub on 14 March 2026."*
    - **Exhibit E30**: Contract Clause 4.2 requiring delivery within 48 hours of dispatch.
  - The Case Twin displays Claims `CLM-17` and `CLM-22` anchored to entities `VendorCorp` and `BuyerLtd`.

---

### [0:40 – 1:00] 3. TARKA-VYUH: Contradiction & Fragility Detection
- **Spoken Narrative**:
  > "Now we run TARKA-VYUH—the adversarial reasoning engine. It does not look for agreement; it hunts for contradictions and fragile dependencies. Instantly, it flags a temporal contradiction between E17 and E22: the dispatch date is conflicted by 48 hours, which directly impacts the statutory breach claim."
- **Visual**:
  - TARKA-VYUH Gauntlet highlights red conflict badge:
    - `CONFLICT_TYPE: TEMPORAL_INCONSISTENCY` (12 March vs 14 March)
    - `AFFECTED_CLAIM: CLM-17 (Dispatch Date)`
    - `FRAGILITY_RATING: HIGH (Load-bearing assumption without corroborating logistics log)`

---

### [1:00 – 1:20] 4. Causal Blast-Radius & Counterfactual Lab
- **Spoken Narrative**:
  > "What happens if the opposing counsel proves the date was actually 14 March? We enter the Counterfactual Lab. By executing an isolated intervention setting the dispatch date to 14 March, the Causal Engine computes the blast-radius: Clause 4.2 breach claim collapses, invalidating $450,000 in liquidated damages, while the base contract validity remains stable."
- **Visual**:
  - Causal graph displays:
    - `Intervention: Set Node(CLM-17) = '14 March 2026'`
    - `Should-Change: Breach_Claim_Clause_4_2 (INVALIDATED)`
    - `Should-Not-Change: Contract_Formation (STABLE)`
    - Blast-Radius Metric: 2 claims downstream affected.

---

### [1:20 – 1:40] 5. Auto-Healer: Evidence-Grounded Repair Proposal
- **Spoken Narrative**:
  > "Rather than leaving the argument broken, the Auto-Healer generates a structured Repair Proposal. It identifies an evidence gap: dispatch was delayed due to customs inspection, supported by carrier tracking notes. It proposes narrowing the breach claim to post-acceptance delay, restoring empirical consistency without inventing facts."
- **Visual**:
  - System presents Repair Candidate:
    - `Candidate ID: REP-2026-08`
    - `Utility Vector: [Evidence Grounding: 0.94, Consistency: 0.98, Claim Preservation: 0.88]`
    - `Action: Replace unqualified dispatch breach with conditional demurrage claim.`

---

### [1:40 – 2:00] 6. Independent Re-Attack Engine
- **Spoken Narrative**:
  > "Most AI systems stop after generating a repair. NYAYA-SATYA does not trust its own repair. It spins up an independent, zero-memory re-attack instance. The re-attack agent tries to invalidate the repair using the surviving exhibits. If the repair survives, it earns an empirical immunity score."
- **Visual**:
  - Independent Re-Attack Terminal:
    - `Re-Attack Vector: Challenge notice requirement under Clause 4.3`
    - `Result: DEFENDED (Notice was contemporaneously served via E31)`
    - `Empirical Immunity: SURVIVED (Confidence: 0.92)`

---

### [2:00 – 2:20] 7. UNWIND Core Governance & Human Legal Gate
- **Spoken Narrative**:
  > "Here is our fundamental safety guarantee: the AI cannot approve its own repair. UNWIND Core locks the state machine in `ASK_HUMAN`. An automated bot cannot approve this transition. Only a credentialed human reviewer can review the legal grounding and authorize acceptance."
- **Visual**:
  - Governance State Machine badge: `STATUS: ASK_HUMAN`.
  - Human reviewer (`human::counsel_lead`) enters credentials and clicks `AUTHORIZE REPAIR`.
  - Proposal cryptographic hash is sealed and committed to the immutable audit log.

---

### [2:20 – 2:40] 8. Dossier 2.0 & Cryptographic Provenance
- **Spoken Narrative**:
  > "The output is not an unverified chat snippet. It is Dossier 2.0: an auditable, versioned judicial dossier. Every claim, contradiction, counterfactual intervention, and repair is cryptographically linked to original SHA-256 exhibit hashes. Opposing counsel, judges, and review partners can verify every step."
- **Visual**:
  - Rendered Dossier 2.0:
    - `Dossier ID: DOS-SYNTHETIC-2026-01`
    - `Content Hash: e3b0c44...`
    - `Parent Hash: a18f32c...`
    - Checklists: Evidence Grounding [VERIFIED], Non-Adjudication [COMPLIANT].

---

### [2:40 – 3:00] 9. Security, Observability, & Honest Impact
- **Spoken Narrative**:
  > "NYAYA-SATYA is built for real production: authenticated Bearer tokens, strict case tenant isolation, rate limiting, and zero PII telemetry. And because we value epistemic honesty, our deployment status explicitly reads `NO_REAL_DEPLOYMENT_DATA_YET`—we refuse to manufacture fake users or fabricated win rates. NYAYA-SATYA: Don't trust the draft. Attack it."
- **Visual**:
  - `GET /health` -> `HEALTHY (200 OK)`
  - `GET /api/nyaya/impact/deployment-status` -> `STATUS: NO_REAL_DEPLOYMENT_DATA_YET (Real Users: 0)`
  - Full Regression Badge: `1,485 passed, 0 failed`.

---

## Reproducible Demonstration CLI Commands

To replicate this exact demonstration locally:

```bash
# 1. Start the API server
uvicorn services.api.main:app --host 127.0.0.1 --port 8080

# 2. Check health & readiness probes
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/ready
curl -s http://127.0.0.1:8080/version

# 3. Ingest Exhibit E17 (Dispatch date 12 March)
curl -X POST http://127.0.0.1:8080/api/nyaya/evidence/upload \
  -H "Authorization: Bearer dev-operator-token" \
  -F "case_id=CASE_SYNTHETIC_DEMO_2026" \
  -F "file=@demo/exhibit_e17.txt"

# 4. Ingest Exhibit E22 (Freight date 14 March)
curl -X POST http://127.0.0.1:8080/api/nyaya/evidence/upload \
  -H "Authorization: Bearer dev-operator-token" \
  -F "case_id=CASE_SYNTHETIC_DEMO_2026" \
  -F "file=@demo/exhibit_e22.txt"

# 5. Build Case Twin & Run Adversarial Analysis
curl -X POST http://127.0.0.1:8080/api/nyaya/twin/build \
  -H "Authorization: Bearer dev-operator-token" \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_SYNTHETIC_DEMO_2026"}'

# 6. Generate Dossier 2.0
curl -X POST http://127.0.0.1:8080/api/nyaya/dossier/build \
  -H "Authorization: Bearer dev-operator-token" \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE_SYNTHETIC_DEMO_2026"}'

# 7. Check Honest Deployment Telemetry
curl -s http://127.0.0.1:8080/api/nyaya/impact/deployment-status \
  -H "Authorization: Bearer dev-operator-token"
```
